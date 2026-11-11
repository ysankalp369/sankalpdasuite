"""FastAPI application – REST API + static web interface."""
from __future__ import annotations

import io
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.orm import Session

from . import ai, knowledge, schema, services, validation
from .db import (AuditLog, Clause, Document, Fact, GeneratedDocument, LegalSource, Project, Review, SessionLocal, Unit, User,
                 init_db, now)
from .drafting.render import render_project
from .security import (ROLES, audit, can, create_session, ensure_bootstrap_admin, hash_password, user_for_token,
                       verify_password)

WEB = Path(__file__).resolve().parent.parent / "web"
app = FastAPI(title="Redevelopment DA Suite", version="1.0")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def current_user(authorization: str | None = Header(default=None), db: Session = Depends(get_db)) -> User:
    tok = (authorization or "").removeprefix("Bearer ").strip()
    u = user_for_token(db, tok)
    if not u:
        raise HTTPException(401, "Not signed in")
    return u


def need(user: User, perm: str):
    if not can(user, perm):
        raise HTTPException(403, f"Your role ({ROLES.get(user.role, user.role)}) is not permitted to {perm.replace('.', ' ')}.")


@app.on_event("startup")
def _startup():
    init_db()
    with SessionLocal() as db:
        cred = ensure_bootstrap_admin(db)
        if cred:
            print(f"[DA Suite] Initial admin credentials written to {cred}")
        knowledge.seed_library(db)
        knowledge.seed_register(db)


# ------------------------------------------------------------------ auth & users
class LoginIn(BaseModel):
    username: str
    password: str


@app.post("/api/login")
def login(body: LoginIn, db: Session = Depends(get_db)):
    u = db.query(User).filter_by(username=body.username).first()
    if not u or not u.active or not verify_password(body.password, u.password_hash):
        raise HTTPException(401, "Invalid username or password")
    tok = create_session(db, u)
    audit(db, u, "auth.login")
    return {"token": tok, "user": _user(u)}


def _user(u: User):
    perms = [p for p in __import__("dacore.security", fromlist=["PERMISSIONS"]).PERMISSIONS if can(u, p)]
    return {"id": u.id, "username": u.username, "full_name": u.full_name, "role": u.role, "role_label": ROLES.get(u.role), "permissions": perms}


@app.get("/api/me")
def me(user: User = Depends(current_user)):
    return _user(user) | {"ai_available": ai.available()}


class UserIn(BaseModel):
    username: str
    full_name: str = ""
    role: str
    password: str


@app.get("/api/users")
def users(user: User = Depends(current_user), db: Session = Depends(get_db)):
    need(user, "users.manage")
    return [_user(u) | {"active": u.active} for u in db.query(User).all()]


@app.post("/api/users")
def add_user(body: UserIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    need(user, "users.manage")
    if body.role not in ROLES:
        raise HTTPException(400, "Unknown role")
    if len(body.password) < 10:
        raise HTTPException(400, "Password must be at least 10 characters")
    if db.query(User).filter_by(username=body.username).first():
        raise HTTPException(400, "Username exists")
    u = User(username=body.username, full_name=body.full_name, role=body.role, password_hash=hash_password(body.password))
    db.add(u); db.commit()
    audit(db, user, "user.create", username_created=body.username, role=body.role)
    return _user(u)


class PwIn(BaseModel):
    old_password: str
    new_password: str


@app.post("/api/me/password")
def change_pw(body: PwIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if not verify_password(body.old_password, user.password_hash) or len(body.new_password) < 10:
        raise HTTPException(400, "Current password incorrect or new password shorter than 10 characters")
    user.password_hash = hash_password(body.new_password); db.commit()
    audit(db, user, "auth.password_change")
    return {"ok": True}


@app.get("/api/roles")
def roles():
    return ROLES


# ------------------------------------------------------------------ dashboard
@app.get("/api/dashboard")
def dashboard(user: User = Depends(current_user), db: Session = Depends(get_db)):
    projects = db.query(Project).order_by(Project.updated_at.desc()).all()
    pending = 0
    for p in projects:
        g = services.gaps(p)
        pending += sum(1 for x in g["missing"] if x["critical"]) + len(g["conflict"])
    return {"projects": len(projects), "reviews": db.query(Review).count(), "clauses": db.query(Clause).count(),
            "clauses_pending": db.query(Clause).filter_by(approval_status="pending_review").count(),
            "generated": db.query(GeneratedDocument).count(), "pending_items": pending,
            "references": db.query(Document).filter_by(category="reference").count(),
            "recent": [_proj_summary(p) for p in projects[:6]], "ai_available": ai.available()}


def _proj_summary(p: Project):
    g = services.gaps(p)
    return {"id": p.id, "name": p.name, "status": p.status, "updated_at": p.updated_at.isoformat(),
            "society": schema.value(p.data, "society.name"), "developer": schema.value(p.data, "developer.name"),
            "units": len(p.units), "documents": len(p.documents),
            "critical_missing": sum(1 for x in g["missing"] if x["critical"]), "conflicts": len(g["conflict"]), "verify": len(g["verify"])}


# ------------------------------------------------------------------ projects
@app.get("/api/schema")
def get_schema():
    return {"groups": schema.GROUPS, "fields": [f.__dict__ for f in schema.FIELDS], "statuses": schema.STATUSES,
            "doc_categories": {"society": "Society documents", "property": "Property and title documents", "members": "Member information",
                               "developer": "Developer documents", "technical": "Technical documents"}}


class ProjectIn(BaseModel):
    name: str
    seed: dict[str, Any] = {}


@app.get("/api/projects")
def projects(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return [_proj_summary(p) for p in db.query(Project).order_by(Project.updated_at.desc()).all()]


@app.post("/api/projects")
def new_project(body: ProjectIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    need(user, "project.create")
    p = services.create_project(db, user, body.name, body.seed)
    return _proj_summary(p)


@app.get("/api/projects/{pid}")
def project(pid: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    p = _proj(db, pid)
    return {"summary": _proj_summary(p), "data": p.data,
            "documents": [_doc(d) for d in p.documents],
            "units": [services.unit_dict(u) for u in p.units],
            "generated": [_gen(g) for g in db.query(GeneratedDocument).filter_by(project_id=pid).order_by(GeneratedDocument.created_at.desc())],
            "reviews": [_rev(r) for r in db.query(Review).filter_by(project_id=pid).order_by(Review.created_at.desc())]}


@app.delete("/api/projects/{pid}")
def del_project(pid: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    need(user, "project.delete")
    p = _proj(db, pid)
    db.query(GeneratedDocument).filter_by(project_id=pid).delete()
    db.delete(p); db.commit()
    audit(db, user, "project.delete", pid)
    return {"ok": True}


def _proj(db, pid) -> Project:
    p = db.get(Project, pid)
    if not p:
        raise HTTPException(404, "Project not found")
    return p


class FieldIn(BaseModel):
    value: Any = None
    status: str = "confirmed"
    note: str = ""


@app.put("/api/projects/{pid}/fields/{key}")
def put_field(pid: int, key: str, body: FieldIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    need(user, "project.edit")
    if body.status not in schema.STATUSES:
        raise HTTPException(400, "Bad status")
    try:
        return services.set_field(db, user, _proj(db, pid), key, body.value, body.status, body.note)
    except KeyError:
        raise HTTPException(404, "Unknown field")


@app.get("/api/projects/{pid}/gaps")
def project_gaps(pid: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return services.gaps(_proj(db, pid))


@app.get("/api/pending")
def pending(user: User = Depends(current_user), db: Session = Depends(get_db)):
    out = []
    for p in db.query(Project).all():
        g = services.gaps(p)
        for kind in ("conflict", "missing", "verify"):
            for x in g[kind]:
                if kind == "missing" and not x["critical"]:
                    continue
                out.append({"project_id": p.id, "project": p.name, "kind": kind, **{k: x[k] for k in ("key", "label", "group", "critical")}})
        for m in g["member_issues"]:
            out.append({"project_id": p.id, "project": p.name, "kind": "member", "key": "", "label": f"Unit {m['unit']}: {m['issue']}", "group": "Members", "critical": False})
    return out


# ------------------------------------------------------------------ documents
@app.post("/api/projects/{pid}/documents")
async def upload(pid: int, category: str = Form(...), use_ai: bool = Form(False), files: list[UploadFile] = File(...),
                 user: User = Depends(current_user), db: Session = Depends(get_db)):
    need(user, "document.upload")
    p = _proj(db, pid)
    out = []
    for f in files:
        data = await f.read()
        try:
            d = services.ingest_document(db, user, p, f.filename, data, category, use_ai)
            out.append(_doc(d))
        except ValueError as e:
            out.append({"filename": f.filename, "error": str(e)})
    return out


def _doc(d: Document):
    return {"id": d.id, "filename": d.filename, "category": d.category, "doc_type": d.doc_type, "doc_type_label": (d.meta or {}).get("doc_type_label", d.doc_type),
            "pages": d.pages, "ocr_used": d.ocr_used, "size": d.size, "sha256": d.sha256, "uploaded_at": d.uploaded_at.isoformat(), "meta": d.meta}


@app.get("/api/documents/{did}")
def document(did: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    d = db.get(Document, did) or _404()
    facts = db.query(Fact).filter_by(document_id=did).all()
    return {"document": _doc(d), "facts": [{"field": f.field, "label": schema.FIELD_MAP[f.field].label if f.field in schema.FIELD_MAP else f.field,
                                            "value": f.value, "page": f.page, "paragraph": f.paragraph, "snippet": f.snippet, "method": f.method, "category": f.category} for f in facts],
            "text": d.text_index[:400]}


class DocTypeIn(BaseModel):
    doc_type: str


@app.put("/api/documents/{did}/type")
def set_doc_type(did: int, body: DocTypeIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    need(user, "project.edit")
    d = db.get(Document, did) or _404()
    d.doc_type = body.doc_type; db.commit()
    audit(db, user, "document.reclassify", d.project_id, document=d.filename, doc_type=body.doc_type)
    return _doc(d)


@app.get("/api/documents/{did}/download")
def doc_download(did: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    need(user, "document.view")
    d = db.get(Document, did) or _404()
    audit(db, user, "document.download", d.project_id, filename=d.filename)
    return _stream(services.load_file(d.stored_name), d.filename)


def _404():
    raise HTTPException(404, "Not found")


# ------------------------------------------------------------------ units
class UnitIn(BaseModel):
    data: dict[str, Any]


@app.post("/api/projects/{pid}/units")
def add_unit(pid: int, body: UnitIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    need(user, "project.edit")
    p = _proj(db, pid)
    u = Unit(project_id=p.id, unit_no=str(body.data.get("unit_no") or "NEW"))
    db.add(u); _apply_unit(u, body.data); db.commit()
    audit(db, user, "unit.create", pid, unit=u.unit_no)
    return services.unit_dict(u)


@app.put("/api/units/{uid}")
def put_unit(uid: int, body: UnitIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    need(user, "project.edit")
    u = db.get(Unit, uid) or _404()
    before = services.unit_dict(u)
    _apply_unit(u, body.data); db.commit()
    audit(db, user, "unit.update", u.project_id, unit=u.unit_no, changes={k: v for k, v in body.data.items() if before.get(k) != v})
    return services.unit_dict(u)


@app.delete("/api/units/{uid}")
def del_unit(uid: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    need(user, "project.edit")
    u = db.get(Unit, uid) or _404()
    pid = u.project_id; db.delete(u); db.commit()
    audit(db, user, "unit.delete", pid, unit_id=uid)
    return {"ok": True}


def _apply_unit(u, data):
    for k, v in data.items():
        if k in services.UNIT_FIELDS and k != "sources":
            if k.endswith("_sqft") or k in ("monthly_rent", "deposit", "brokerage", "shifting", "corpus", "hardship", "society_dues"):
                v = None if v in ("", None) else float(v)
            setattr(u, k, v)


# ------------------------------------------------------------------ generation & validation
class GenIn(BaseModel):
    kinds: list[str] = ["da", "annexures", "paaa", "validation"]


@app.get("/api/projects/{pid}/validate")
def validate_project(pid: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    p = _proj(db, pid)
    units = [services.unit_dict(u) for u in p.units]
    res = render_project(p.data, units, [{"doc_type": d.doc_type, "filename": d.filename} for d in p.documents])
    checks = validation.validate(res, p.data, units, services.reference_markers(db))
    return {"checks": checks, "summary": validation.summary(checks), "outstanding": res.outstanding, "unverified": res.unverified,
            "calc": res.calc}


@app.post("/api/projects/{pid}/generate")
def generate(pid: int, body: GenIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    need(user, "draft.generate")
    out = services.generate(db, user, _proj(db, pid), tuple(body.kinds))
    return {"validation": out["validation"], "files": [_gen(g) for g in out["files"]]}


def _gen(g: GeneratedDocument):
    return {"id": g.id, "kind": g.kind, "title": g.title, "filename": g.filename, "version": g.version, "status": g.status,
            "created_at": g.created_at.isoformat(), "meta": g.meta, "project_id": g.project_id, "review_id": g.review_id}


@app.get("/api/generated")
def generated(project_id: int | None = None, user: User = Depends(current_user), db: Session = Depends(get_db)):
    q = db.query(GeneratedDocument)
    if project_id:
        q = q.filter_by(project_id=project_id)
    return [_gen(g) for g in q.order_by(GeneratedDocument.created_at.desc()).limit(500)]


@app.get("/api/generated/{gid}/download")
def gen_download(gid: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    g = db.get(GeneratedDocument, gid) or _404()
    need(user, "download.sensitive" if (g.sensitive and g.status == "finalised") else "download.draft")
    audit(db, user, "generated.download", g.project_id, filename=g.filename, version=g.version)
    return _stream(services.load_file(g.stored_name), g.filename)


@app.post("/api/generated/{gid}/finalise")
def finalise(gid: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    need(user, "draft.finalise")
    g = db.get(GeneratedDocument, gid) or _404()
    if g.kind == "da" and not (g.meta or {}).get("summary", {}).get("execution_ready"):
        raise HTTPException(400, "This draft has unresolved critical items (blanks, conflicts or failed checks) and cannot be finalised.")
    g.status = "finalised"; db.commit()
    audit(db, user, "generated.finalise", g.project_id, filename=g.filename, version=g.version)
    return _gen(g)


def _stream(data: bytes, filename: str):
    mt = {"docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
          "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "zip": "application/zip", "pdf": "application/pdf"}.get(filename.rsplit(".", 1)[-1].lower(), "application/octet-stream")
    from urllib.parse import quote
    return StreamingResponse(io.BytesIO(data), media_type=mt, headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"})


# ------------------------------------------------------------------ review
@app.post("/api/reviews")
async def new_review(file: UploadFile = File(...), project_id: int | None = Form(None), use_ai: bool = Form(False),
                     user: User = Depends(current_user), db: Session = Depends(get_db)):
    need(user, "review.run")
    if not file.filename.lower().endswith(".docx"):
        raise HTTPException(400, "Track Changes review requires a .docx file (convert .doc / PDF to Word first).")
    data = await file.read()
    p = db.get(Project, project_id) if project_id else None
    rv = services.run_review(db, user, file.filename, data, p, use_ai)
    return _rev(rv, full=True)


def _rev(r: Review, full=False):
    d = {"id": r.id, "title": r.title, "project_id": r.project_id, "created_at": r.created_at.isoformat(), "summary": r.summary}
    if full:
        d["findings"] = r.findings
    return d


@app.get("/api/reviews")
def reviews(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return [_rev(r) for r in db.query(Review).order_by(Review.created_at.desc())]


@app.get("/api/reviews/{rid}")
def review(rid: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    r = db.get(Review, rid) or _404()
    return _rev(r, full=True) | {"files": [_gen(g) for g in db.query(GeneratedDocument).filter_by(review_id=rid)]}


# ------------------------------------------------------------------ comparison
@app.post("/api/compare")
async def compare(file_a: UploadFile = File(...), file_b: UploadFile = File(...), user: User = Depends(current_user), db: Session = Depends(get_db)):
    need(user, "review.run")
    g = services.compare_documents(db, user, file_a.filename, await file_a.read(), file_b.filename, await file_b.read())
    return _gen(g)


# ------------------------------------------------------------------ clause library
def _clause(c: Clause):
    return {k: getattr(c, k) for k in ("id", "clause_code", "subject", "article", "standard_wording", "alternative_wording", "society_favourable",
                                       "neutral_version", "source_agreement", "legal_provision", "explanation", "risk_addressed", "recommended_use",
                                       "related", "classification", "approval_status", "contains_project_facts", "topic")}


@app.get("/api/clauses")
def clauses(q: str = "", topic: str | None = None, status: str | None = None, classification: str | None = None, source: str | None = None,
            limit: int = 100, user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = knowledge.search(db, q, topic or None, status or None, classification or None, limit=2000 if source else limit)
    if source:
        rows = [r for r in rows if r.source_agreement == source][:limit]
    return {"items": [_clause(c) for c in rows], "topics": list(knowledge.TOPICS) + ["general"],
            "sources": sorted({s for (s,) in db.query(Clause.source_agreement).distinct()})}


class ClauseIn(BaseModel):
    subject: str
    standard_wording: str
    alternative_wording: str = ""
    society_favourable: str = ""
    neutral_version: str = ""
    legal_provision: str = ""
    explanation: str = ""
    risk_addressed: str = ""
    recommended_use: str = ""
    classification: str = "Negotiable"
    topic: str = "general"


@app.post("/api/clauses")
def propose_clause(body: ClauseIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    need(user, "clause.propose")
    n = db.query(Clause).filter(Clause.clause_code.like("USR-%")).count() + 1
    c = Clause(clause_code=f"USR-{n:04d}", source_agreement=f"Proposed by {user.username}", approval_status="pending_review", **body.model_dump())
    db.add(c); db.commit()
    audit(db, user, "clause.propose", code=c.clause_code)
    return _clause(c)


@app.put("/api/clauses/{cid}")
def edit_clause(cid: int, body: ClauseIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    need(user, "clause.propose")
    c = db.get(Clause, cid) or _404()
    for k, v in body.model_dump().items():
        setattr(c, k, v)
    if not can(user, "clause.approve"):
        c.approval_status = "pending_review"
    db.commit()
    audit(db, user, "clause.edit", code=c.clause_code)
    return _clause(c)


@app.post("/api/clauses/{cid}/{action}")
def clause_action(cid: int, action: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    need(user, "clause.approve")
    c = db.get(Clause, cid) or _404()
    if action not in ("approve", "reject", "reopen"):
        raise HTTPException(400, "Bad action")
    if action == "approve" and c.contains_project_facts:
        raise HTTPException(400, "This clause contains project-specific facts (names, amounts, plot details). Edit it into a generic form before approval.")
    c.approval_status = {"approve": "approved", "reject": "rejected", "reopen": "pending_review"}[action]
    c.approved_by, c.approved_at = (user.id, now()) if action == "approve" else (None, None)
    db.commit()
    audit(db, user, f"clause.{action}", code=c.clause_code)
    return _clause(c)


# ------------------------------------------------------------------ reference knowledge base
@app.post("/api/references")
async def add_reference(files: list[UploadFile] = File(...), user: User = Depends(current_user), db: Session = Depends(get_db)):
    need(user, "clause.propose")
    return [services.ingest_reference_agreement(db, user, f.filename, await f.read()) for f in files]


@app.get("/api/references")
def list_references(user: User = Depends(current_user), db: Session = Depends(get_db)):
    out = []
    for d in db.query(Document).filter_by(category="reference"):
        fs = (d.meta or {}).get("findings", [])
        out.append(_doc(d) | {"clauses": (d.meta or {}).get("clauses"), "findings_count": len(fs),
                              "counts": {s: sum(1 for f in fs if f["severity"] == s) for s in ("Critical", "High", "Medium", "Low")}})
    return out


@app.get("/api/references/matrix")
def matrix(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return services.reference_matrix(db)


# ------------------------------------------------------------------ legal research
def _legal(l: LegalSource):
    return {k: getattr(l, k) for k in ("id", "code", "title", "kind", "provision", "proposition", "source_ref", "effective_version", "verified_on", "verification_status", "topics")}


@app.get("/api/legal")
def legal(q: str = "", user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.query(LegalSource).all()
    if q:
        ql = q.lower().split()
        rows = [r for r in rows if all(w in (r.title + r.provision + r.proposition + " ".join(r.topics or [])).lower() for w in ql)]
    return [_legal(r) for r in rows]


class LegalIn(BaseModel):
    code: str
    title: str
    kind: str
    provision: str = ""
    proposition: str = ""
    source_ref: str = ""
    effective_version: str = ""
    verified_on: str = ""
    verification_status: str = "advocate verification required"
    topics: list[str] = []


@app.post("/api/legal")
def add_legal(body: LegalIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    need(user, "legal.edit")
    l = LegalSource(**body.model_dump()); db.add(l); db.commit()
    audit(db, user, "legal.add", code=l.code)
    return _legal(l)


@app.put("/api/legal/{lid}")
def edit_legal(lid: int, body: LegalIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    need(user, "legal.edit")
    l = db.get(LegalSource, lid) or _404()
    for k, v in body.model_dump().items():
        setattr(l, k, v)
    db.commit()
    audit(db, user, "legal.edit", code=l.code, status=l.verification_status)
    return _legal(l)


class AskIn(BaseModel):
    question: str


@app.post("/api/legal/ask")
def ask(body: AskIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if not ai.available():
        raise HTTPException(400, "Claude is not configured on this server (set ANTHROPIC_API_KEY). The register can still be searched.")
    out = ai.legal_research(body.question, [_legal(r) for r in db.query(LegalSource).all()])
    audit(db, user, "legal.ask", question=body.question[:200])
    return out


# ------------------------------------------------------------------ audit
@app.get("/api/audit")
def audit_log(project_id: int | None = None, user: User = Depends(current_user), db: Session = Depends(get_db)):
    need(user, "audit.view")
    q = db.query(AuditLog)
    if project_id:
        q = q.filter_by(project_id=project_id)
    return [{"at": a.at.isoformat(), "user": a.username, "project_id": a.project_id, "action": a.action, "detail": a.detail}
            for a in q.order_by(AuditLog.at.desc()).limit(500)]


# ------------------------------------------------------------------ static UI
app.mount("/static", StaticFiles(directory=WEB), name="static")


@app.get("/")
def index():
    return FileResponse(WEB / "index.html")
