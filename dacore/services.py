"""Application services: the workflows behind the API (kept framework-independent for testing)."""
from __future__ import annotations

import hashlib
import io
import json
import re
import uuid
import zipfile

from sqlalchemy.orm import Session

from . import ai, extract, ingest, knowledge, schema, validation
from .config import OUTPUT_DIR, REVIEW_AUTHOR, STORAGE_DIR
from .db import Document, Fact, GeneratedDocument, Project, Review, Unit, User
from .drafting import annexure_texts as AX
from .drafting.docx_builder import build_docx
from .drafting.render import Renderer, render_project
from .review import reports
from .review.redline import DocxDoc, accept_all
from .review.reviewer import findings_dicts, review_docx
from .security import audit, read_encrypted, write_encrypted

UNIT_FIELDS = ["unit_no", "building", "floor", "unit_type", "use", "holders", "existing_rera_carpet_sqft", "existing_mofa_carpet_sqft",
               "existing_builtup_sqft", "new_rera_carpet_sqft", "balcony_sqft", "additional_purchased_sqft", "parking", "monthly_rent",
               "deposit", "brokerage", "shifting", "corpus", "hardship", "share_cert_no", "consent", "mortgage", "bank_noc", "status",
               "society_dues", "sources", "notes"]


def unit_dict(u: Unit) -> dict:
    d = {k: getattr(u, k) for k in UNIT_FIELDS}
    d["id"] = u.id
    return d


# ------------------------------------------------------------------ storage
def store_file(data: bytes) -> str:
    name = uuid.uuid4().hex
    write_encrypted(STORAGE_DIR / name, data)
    return name


def load_file(stored: str) -> bytes:
    p = STORAGE_DIR / stored
    if not p.exists():
        p = OUTPUT_DIR / stored
    return read_encrypted(p)


def save_output(db: Session, user: User | None, kind: str, title: str, filename: str, data: bytes, project_id=None, review_id=None,
                meta=None, sensitive=True) -> GeneratedDocument:
    name = uuid.uuid4().hex
    write_encrypted(OUTPUT_DIR / name, data)
    prev = db.query(GeneratedDocument).filter_by(project_id=project_id, kind=kind).count() if project_id else 0
    g = GeneratedDocument(project_id=project_id, review_id=review_id, kind=kind, title=title, stored_name=name, filename=filename,
                          version=prev + 1, meta=meta or {}, sensitive=sensitive, created_by=user.id if user else None)
    db.add(g); db.commit()
    return g


# ------------------------------------------------------------------ projects
def create_project(db: Session, user: User | None, name: str, seed: dict | None = None) -> Project:
    data = schema.initial_data()
    for k, v in (seed or {}).items():
        if k in data and v not in (None, ""):
            data[k] = {"value": v, "status": "confirmed", "sources": [{"doc": "Entered by user"}], "note": ""}
    p = Project(name=name, data=data, created_by=user.id if user else None)
    db.add(p); db.commit()
    audit(db, user, "project.create", p.id, name=name)
    return p


def set_field(db: Session, user: User | None, project: Project, key: str, value, status: str = "confirmed", note: str = "") -> dict:
    if key not in schema.FIELD_MAP:
        raise KeyError(key)
    data = dict(project.data)
    old = data.get(key) or {}
    if status == "na":
        value = None
    entry = {"value": value, "status": status, "sources": old.get("sources", []) if status != "na" else [],
             "note": note or ("Verified by " + (user.username if user else "user")), "candidates": old.get("candidates", []) if status == "conflict" else []}
    data[key] = entry
    project.data = data
    db.commit()
    audit(db, user, "field.set", project.id, field=key, value=value, status=status, previous=old.get("value"))
    return entry


def ingest_document(db: Session, user: User | None, project: Project | None, filename: str, data: bytes, category: str,
                    use_ai: bool = False) -> Document:
    parsed = ingest.read_any(filename, data)
    doc_type = ingest.classify(filename, parsed.text, category)
    doc = Document(project_id=project.id if project else None, category=category, doc_type=doc_type, filename=filename,
                   stored_name=store_file(data), sha256=hashlib.sha256(data).hexdigest(), size=len(data),
                   ocr_used=parsed.ocr_used, pages=parsed.pages, uploaded_by=user.id if user else None,
                   text_index=[{"page": s["page"], "para": s["para"], "text": s["text"][:2000]} for s in parsed.segments[:6000]],
                   meta={"tables": len(parsed.tables), "warnings": parsed.warnings, "doc_type_label": ingest.DOC_TYPE_LABELS.get(doc_type, doc_type)})
    db.add(doc); db.commit()
    audit(db, user, "document.upload", project.id if project else None, filename=filename, doc_type=doc_type, sha256=doc.sha256)
    if project is None:
        return doc
    facts = extract.run_rules(parsed.segments, doc_type)
    if use_ai and ai.available():
        try:
            for f in ai.extract_facts(parsed.text, doc_type):
                k = parsed.text.find(f["quote"][:60])
                seg = next((s for s in parsed.segments if f["quote"][:40] in s["text"]), {})
                facts.append({"field": f["field"], "value": f["value"], "normalized": extract.normalize(extract._kind(schema.FIELD_MAP[f["field"]]), f["value"]),
                              "page": seg.get("page"), "paragraph": seg.get("para"), "snippet": f["quote"], "method": "ai", "confidence": 0.7,
                              "category": schema.FIELD_MAP[f["field"]].category})
        except Exception as e:  # AI is optional; never block intake
            doc.meta = {**doc.meta, "ai_error": str(e)[:300]}
    for f in facts:
        db.add(Fact(project_id=project.id, document_id=doc.id, **{k: f[k] for k in ("field", "value", "normalized", "page", "paragraph", "snippet", "method", "confidence", "category")}))
    db.commit()
    # member register
    units = extract.parse_member_tables(parsed.tables, filename, doc.id)
    if units:
        doc.doc_type = "member_register"
        merge_units(db, project, units)
    recompute(db, project)
    doc.meta = {**doc.meta, "facts": len(facts), "units": len(units)}
    db.commit()
    return doc


def merge_units(db: Session, project: Project, units: list[dict]):
    existing = {(u.building or "", u.unit_no.strip().lower()): u for u in project.units}
    for nu in units:
        key = (nu.get("building") or "", nu["unit_no"].strip().lower())
        cur = existing.get(key)
        if cur is None:
            cur = Unit(project_id=project.id, unit_no=nu["unit_no"])
            db.add(cur); existing[key] = cur
            for k in UNIT_FIELDS:
                if k in nu and nu[k] not in (None, ""):
                    setattr(cur, k, nu[k])
            continue
        # differing values from a second register -> recorded as discrepancy notes, not overwritten
        notes = []
        for k in ("existing_rera_carpet_sqft", "new_rera_carpet_sqft"):
            a, b = getattr(cur, k), nu.get(k)
            if a is not None and b is not None and abs(float(a) - float(b)) > 0.5:
                notes.append(f"{k}: {a} vs {b} in {nu['sources'][0]['doc']}")
            elif a is None and b is not None:
                setattr(cur, k, b)
        if notes:
            cur.notes = ((cur.notes or "") + " | DISCREPANCY " + "; ".join(notes)).strip(" |")
        cur.sources = (cur.sources or []) + nu.get("sources", [])
    db.commit()


def recompute(db: Session, project: Project):
    facts = db.query(Fact).filter_by(project_id=project.id).all()
    docs = {d.id: {"filename": d.filename} for d in project.documents}
    data = dict(project.data)
    # reset non-user entries before re-consolidating
    for k, e in list(data.items()):
        if e.get("status") in ("extracted", "verify", "conflict") and not any(s.get("doc") == "Entered by user" for s in e.get("sources", [])):
            if e.get("status") == "conflict" and any(c.get("label") == "previously confirmed" for c in e.get("candidates", [])):
                continue
            data[k] = schema.empty_entry(schema.FIELD_MAP[k]) if k in schema.FIELD_MAP else e
    data = extract.consolidate(data, [{"document_id": f.document_id, "field": f.field, "value": f.value, "normalized": f.normalized,
                                       "page": f.page, "paragraph": f.paragraph, "snippet": f.snippet, "method": f.method} for f in facts], docs)
    project.data = data
    db.commit()


def gaps(project: Project) -> dict:
    out = {"missing": [], "verify": [], "conflict": [], "na": [], "member_issues": []}
    for f in schema.FIELDS:
        e = project.data.get(f.key) or {}
        st = e.get("status", "missing")
        item = {"key": f.key, "label": f.label, "group": f.group, "critical": f.critical, "candidates": e.get("candidates", []), "sources": e.get("sources", [])}
        if st == "missing":
            out["missing"].append(item)
        elif st in ("verify", "extracted"):
            out["verify"].append(item | {"value": e.get("value")})
        elif st == "conflict":
            out["conflict"].append(item)
        elif st == "na":
            out["na"].append(item)
    units = [unit_dict(u) for u in project.units]
    for u in units:
        if not u["holders"]:
            out["member_issues"].append({"unit": u["unit_no"], "issue": "No holder recorded"})
        if u["new_rera_carpet_sqft"] is None:
            out["member_issues"].append({"unit": u["unit_no"], "issue": "New RERA carpet area missing"})
        if (u["status"] or "regular") != "regular":
            out["member_issues"].append({"unit": u["unit_no"], "issue": f"Status: {u['status']}"})
        if "DISCREPANCY" in (u["notes"] or ""):
            out["member_issues"].append({"unit": u["unit_no"], "issue": u["notes"]})
    return out


# ------------------------------------------------------------------ generation
def generate(db: Session, user: User | None, project: Project, kinds=("da", "annexures", "paaa", "validation")) -> dict:
    units = [unit_dict(u) for u in project.units]
    docs = [{"doc_type": d.doc_type, "filename": d.filename} for d in project.documents]
    res = render_project(project.data, units, docs)
    checks = validation.validate(res, project.data, units, reference_markers(db))
    summ = validation.summary(checks)
    banner = None if summ["execution_ready"] else "DRAFT FOR ADVOCATE REVIEW – NOT FOR EXECUTION – CONTAINS OUTSTANDING / UNVERIFIED INFORMATION"
    title = f"Development Agreement – {schema.value(project.data, 'society.name') or project.name}"
    out = {"validation": {"checks": checks, "summary": summ, "outstanding": res.outstanding, "unverified": res.unverified}, "files": []}
    meta = {"summary": summ, "outstanding": len(res.outstanding), "critical_outstanding": sum(o["critical"] for o in res.outstanding)}
    safe = re.sub(r"[^A-Za-z0-9]+", "_", project.name)[:40]
    if "da" in kinds:
        g = save_output(db, user, "da", title, f"DA_{safe}_v{_ver(db, project, 'da')}.docx", build_docx(res.blocks, title, banner), project.id, meta=meta)
        out["files"].append(g)
    if "annexures" in kinds:
        blocks = _annexure_blocks(res.blocks)
        g = save_output(db, user, "annexures", "Schedules and Annexures", f"Schedules_Annexures_{safe}.docx", build_docx(blocks, title + " – Schedules & Annexures", banner), project.id, meta=meta)
        out["files"].append(g)
    if "paaa" in kinds and units:
        g = save_output(db, user, "paaa", "Member-wise PAAA drafts", f"PAAA_pack_{safe}.zip", _paaa_pack(project.data, units, banner), project.id, meta={"units": len(units)})
        out["files"].append(g)
    if "validation" in kinds:
        g = save_output(db, user, "validation", "Validation & consistency report", f"Validation_Report_{safe}.docx",
                        reports.validation_report(checks, res.outstanding, res.unverified, title), project.id, meta=summ, sensitive=False)
        out["files"].append(g)
    project.status = "draft generated"
    db.commit()
    audit(db, user, "da.generate", project.id, files=[f.filename for f in out["files"]], **summ)
    return out


def _ver(db, project, kind):
    return db.query(GeneratedDocument).filter_by(project_id=project.id, kind=kind).count() + 1


def _annexure_blocks(blocks):
    out, on = [], False
    for b in blocks:
        if b["t"] == "schedule":
            on = True
        if b["t"] == "signatures":
            on = False
            continue
        if b["t"] == "witness":
            continue
        if b["t"] == "annexure":
            on = True
        if on:
            out.append(b)
    return out


def _paaa_pack(data, units, banner) -> bytes:
    from .textutil import to_float
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, "w", zipfile.ZIP_DEFLATED) as z:
        for u in units:
            r = Renderer(data, [u])
            r._number()
            blocks = [{"t": "heading", "text": "PERMANENT ALTERNATE ACCOMMODATION AGREEMENT"}]
            holders = " and ".join(h.get("name", "") for h in u.get("holders") or []) or "[● MEMBER NAME – OUTSTANDING]"
            for para in AX.PAAA_FORMAT[1:]:
                para = (para.replace("[NAME OF EXISTING MEMBER(S)]", holders).replace("[UNIT NO.]", str(u.get("unit_no")))
                        .replace("[EXISTING AREA]", str(u.get("existing_rera_carpet_sqft") or "[● existing area]"))
                        .replace("[NEW AREA]", str(u.get("new_rera_carpet_sqft") or "[● new area]"))
                        .replace("[PARKING]", str(u.get("parking") or schema.value(data, "tech.parking_per_unit") or "[●]")))
                blocks.append({"t": "para", "runs": r.runs(para)})
            blocks.append({"t": "signatures", "blocks": [
                {"party": "DEVELOPER", "name": schema.value(data, "developer.name") or "", "signers": [("Authorised Signatory", "Developer")]},
                {"party": "EXISTING MEMBER(S)", "name": "", "signers": [(h.get("name", ""), "Member") for h in u.get("holders") or []]},
                {"party": "SOCIETY (Confirming Party)", "name": schema.value(data, "society.name") or "", "signers": [("Chairman", ""), ("Secretary", "")]}]})
            fname = re.sub(r"[^A-Za-z0-9]+", "_", str(u.get("unit_no")))
            z.writestr(f"PAAA_{fname}.docx", build_docx(blocks, f"PAAA – Unit {u.get('unit_no')}", banner))
    return bio.getvalue()


# ------------------------------------------------------------------ review
def run_review(db: Session, user: User | None, filename: str, data: bytes, project: Project | None = None, use_ai: bool = False) -> Review:
    doc = Document(project_id=project.id if project else None, category="review", doc_type="development_agreement", filename=filename,
                   stored_name=store_file(data), sha256=hashlib.sha256(data).hexdigest(), size=len(data), uploaded_by=user.id if user else None)
    db.add(doc); db.commit()
    suggestions = []
    if use_ai and ai.available():
        try:
            suggestions = ai.review_suggestions(DocxDoc(data).texts())
        except Exception as e:
            suggestions = []
            doc.meta = {"ai_error": str(e)[:300]}
    res = review_docx(data, REVIEW_AUTHOR, suggestions)
    fd = findings_dicts(res)
    rv = Review(project_id=project.id if project else None, document_id=doc.id, title=filename, findings=fd,
                summary={"stats": res.stats, "terms": res.terms, "checklist": res.checklist,
                         "counts": {s: sum(1 for f in fd if f["severity"] == s) for s in ("Critical", "High", "Medium", "Low")},
                         "applied": sum(1 for f in fd if f["status"] == "applied"), "refused": sum(1 for f in fd if f["status"] == "refused"),
                         "original_sha256": res.original_sha256},
                created_by=user.id if user else None)
    db.add(rv); db.commit()
    stem = re.sub(r"\.docx$", "", filename, flags=re.I)
    pid = project.id if project else None
    save_output(db, user, "review.original", "Original DA (unmodified)", filename, data, pid, rv.id)
    save_output(db, user, "review.redline", "Redlined DA (Track Changes)", f"{stem}_REDLINE.docx", res.redline, pid, rv.id, meta=res.stats)
    save_output(db, user, "review.clean", "Clean revised DA", f"{stem}_CLEAN.docx", res.clean, pid, rv.id)
    save_output(db, user, "review.report", "Legal Review Report", f"{stem}_Legal_Review_Report.docx", reports.legal_review_report(fd, filename, res.stats), pid, rv.id)
    save_output(db, user, "review.missing", "Missing Clauses Report", f"{stem}_Missing_Clauses.docx", reports.missing_clauses_report(fd, filename), pid, rv.id)
    save_output(db, user, "review.risk", "Society Risk Matrix", f"{stem}_Risk_Matrix.xlsx", reports.risk_matrix_xlsx(fd, filename), pid, rv.id)
    save_output(db, user, "review.compare", "Clause Comparison", f"{stem}_Clause_Comparison.docx", reports.clause_comparison(fd, filename), pid, rv.id)
    save_output(db, user, "review.negotiation", "Negotiation Report", f"{stem}_Negotiation_Report.docx", reports.negotiation_report(fd, filename), pid, rv.id)
    save_output(db, user, "review.checklist", "Execution Checklist", f"{stem}_Execution_Checklist.docx", reports.execution_checklist_report(res.checklist, filename), pid, rv.id)
    audit(db, user, "review.run", pid, review_id=rv.id, filename=filename, **rv.summary["counts"])
    return rv


# ------------------------------------------------------------------ document comparison (redline of two versions)
def compare_documents(db: Session, user: User | None, name_a: str, a: bytes, name_b: str, b: bytes) -> GeneratedDocument:
    """Produce a Track Changes document showing how version B differs from version A (paragraph-level, word diff)."""
    import difflib
    from .review.redline import Edit, NewPara
    da, db_ = DocxDoc(a), DocxDoc(b)
    ta, tb = da.texts(), db_.texts()
    sm = difflib.SequenceMatcher(a=ta, b=tb, autojunk=False)
    edits, newp = [], []
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal":
            continue
        similar = op == "replace" and (i2 - i1) == (j2 - j1) and all(
            difflib.SequenceMatcher(a=ta[i1 + k], b=tb[j1 + k]).quick_ratio() > 0.5 for k in range(i2 - i1))
        if similar:
            for k in range(i2 - i1):
                edits.extend(_word_edits(i1 + k, ta[i1 + k], tb[j1 + k]))
        else:
            for k in range(i1, i2):
                if ta[k].strip():
                    edits.append(Edit(k, 0, len(ta[k]), "", "", f"del{k}", delete_mark=True))
            anchor = max(i1 - 1, 0) if i2 == i1 else i2 - 1
            for k in range(j2 - 1, j1 - 1, -1):
                if tb[k].strip():
                    newp.append(NewPara(anchor, tb[k], "", f"ins{k}"))
    da.apply(edits, newp, [], author=REVIEW_AUTHOR)
    out = da.save()
    g = save_output(db, user, "compare", f"Comparison: {name_a} → {name_b}", f"Compare_{re.sub(r'.docx$', '', name_a)}_vs_{re.sub(r'.docx$', '', name_b)}.docx", out)
    audit(db, user, "document.compare", None, a=name_a, b=name_b)
    return g


def _word_edits(pi, old, new):
    import difflib
    from .review.redline import Edit
    toks_o = re.findall(r"\s+|[^\s]+", old)
    toks_n = re.findall(r"\s+|[^\s]+", new)
    sm = difflib.SequenceMatcher(a=toks_o, b=toks_n, autojunk=False)
    pos = [0]
    for t in toks_o:
        pos.append(pos[-1] + len(t))
    out = []
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op != "equal":
            out.append(Edit(pi, pos[i1], pos[i2], "".join(toks_n[j1:j2]), "", f"w{pi}_{i1}"))
    return out


# ------------------------------------------------------------------ reference knowledge base
def ingest_reference_agreement(db: Session, user: User | None, filename: str, data: bytes) -> dict:
    doc = ingest_document(db, user, None, filename, data, "reference")
    texts = DocxDoc(data).texts() if filename.lower().endswith(".docx") else [s["text"] for s in doc.text_index]
    name = re.sub(r"\.(docx|pdf)$", "", filename, flags=re.I)
    added = knowledge.ingest_reference(db, name, texts)
    rv = review_docx(data, REVIEW_AUTHOR) if filename.lower().endswith(".docx") else None
    doc.meta = {**doc.meta, "reference": True, "clauses": added, "findings": findings_dicts(rv) if rv else []}
    db.commit()
    audit(db, user, "reference.ingest", None, filename=filename, **{k: v for k, v in added.items() if isinstance(v, int)})
    return {"document_id": doc.id, **added}


GENERIC_WORDS = {"the", "this", "said", "between", "and", "existing", "project", "society", "solvency", "developer", "redevelopment",
                 "development", "agreement", "new", "shri", "smt", "mr", "mrs", "co-operative", "cooperative", "housing", "private",
                 "limited", "ltd", "pvt", "llp", "m/s", "members", "member", "infra", "infracon", "realty", "developers", "builders"}


_VOCAB: set[str] = set()


def _template_vocab() -> set[str]:
    """Every word used in the master template – such words are generic, never reference-specific."""
    if not _VOCAB:
        from .drafting import master_da
        parts = [t for _l, t in master_da.PARTIES] + [r.text for r in master_da.RECITALS] + [d.text for d in master_da.DEFINITIONS]
        stack = [c for a in master_da.ARTICLES for c in a.clauses]
        while stack:
            c = stack.pop(); parts.append(c.text); stack.extend(c.sub)
        parts += [p for fmt in AX.ANNEXURE_FORMATS.values() for p in fmt]
        _VOCAB.update(w.lower() for w in re.findall(r"[A-Za-z]+", " ".join(parts)))
        _VOCAB.update(GENERIC_WORDS)
    return _VOCAB


def reference_markers(db: Session) -> list[str]:
    """Party names, PANs, plot numbers and sectors found in ingested reference agreements."""
    markers: set[str] = set()
    for d in db.query(Document).filter(Document.category == "reference"):
        text = "\n".join(s["text"] for s in (d.text_index or [])[:120])
        for rule in extract.RULES:
            if rule.field in ("society.name", "developer.name"):
                for m in re.finditer(rule.pattern, text, rule.flags):
                    name = m.group(1).strip(" ,.")
                    words = [w for w in re.sub(r"^(?:M/s\.?\s*)", "", name).split() if w.lower().strip(".,") not in GENERIC_WORDS]
                    w = words[0].strip(".,") if words else ""
                    if len(w) > 3 and w[0].isupper() and w.lower() not in _template_vocab():
                        markers.add(w)
        markers.update(re.findall(r"\b[A-Z]{5}\d{4}[A-Z]\b", text))
        markers.update(x.strip() for x in re.findall(r"Plot\s*No\.?\s*(\d+/\d+\s?[A-Z]?)\b", text))
    return sorted(markers)


def reference_matrix(db: Session) -> list[dict]:
    refs = db.query(Document).filter(Document.category == "reference").all()
    data = {}
    for d in refs:
        if not (d.meta or {}).get("findings") and not d.filename.lower().endswith(".docx"):
            continue
        texts = [s["text"] for s in d.text_index]
        data[re.sub(r"\.(docx|pdf)$", "", d.filename, flags=re.I)] = (texts, (d.meta or {}).get("findings", []))
    return knowledge.comparative_matrix(data)
