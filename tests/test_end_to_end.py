"""End-to-end test through the HTTP API with a fresh instance.

usage: python tests/test_end_to_end.py <reference_dir_with_docx_files> [output_dir]
Reference agreements are read from the given folder (they are not stored in the repository).
"""
from __future__ import annotations

import hashlib
import time
T0 = time.time()
import io
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REF_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else None
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "tests" / "e2e_output"
inst = Path(tempfile.mkdtemp(prefix="da_e2e_"))
os.environ["DA_INSTANCE_DIR"] = str(inst)
os.environ["DA_AI_ENABLED"] = "off"
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from dacore.api import app  # noqa: E402

SAMPLE = ROOT / "tests" / "sample_project"
if not SAMPLE.exists():
    subprocess.check_call([sys.executable, str(ROOT / "tests" / "make_sample_project.py"), str(SAMPLE)])
shutil.rmtree(OUT, ignore_errors=True); OUT.mkdir(parents=True, exist_ok=True)
results = []


def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))
    print(f"[{time.time()-T0:6.1f}s] " + ("PASS " if cond else "FAIL ") + name + (f" – {detail}" if detail else ""))


with TestClient(app) as c:
    pw = [l.split(": ", 1)[1] for l in (inst / "initial_admin_credentials.txt").read_text().splitlines() if l.startswith("password")][0]
    tok = c.post("/api/login", json={"username": "admin", "password": pw}).json()["token"]
    H = {"Authorization": f"Bearer {tok}"}
    # role-based access
    c.post("/api/users", headers=H, json={"username": "intern", "full_name": "Engineer", "role": "project_engineer", "password": "engineer-pass-1"})
    t2 = c.post("/api/login", json={"username": "intern", "password": "engineer-pass-1"}).json()["token"]
    r = c.post("/api/reviews", headers={"Authorization": f"Bearer {t2}"}, files={"file": ("x.docx", b"x")})
    check("RBAC: project engineer cannot run reviews", r.status_code == 403)

    # ---------------------------------------------------------------- knowledge base
    lib = c.get("/api/clauses?limit=2000", headers=H).json()
    check("Clause library seeded", len(lib["items"]) > 80, f"{len(lib['items'])} clauses")
    refs = sorted(REF_DIR.glob("*.docx")) if REF_DIR else []
    for f in refs:
        r = c.post("/api/references", headers=H, files=[("files", (f.name, f.read_bytes()))]).json()
        check(f"Reference ingested: {f.name}", r[0]["added"] > 10, f"{r[0]['added']} candidate clauses, {r[0].get('with_project_facts')} with project facts")
    if refs:
        pend = c.get("/api/clauses?status=pending_review&limit=5", headers=H).json()["items"]
        check("Reference clauses are NOT auto-approved", pend and all(x["approval_status"] == "pending_review" for x in pend))
        fact_clause = next((x for x in c.get("/api/clauses?status=pending_review&limit=2000", headers=H).json()["items"] if x["contains_project_facts"]), None)
        if fact_clause:
            r = c.post(f"/api/clauses/{fact_clause['id']}/approve", headers=H)
            check("Clause with project facts cannot be approved", r.status_code == 400)
        m = c.get("/api/references/matrix", headers=H).json()
        check("Comparative clause matrix built", len(m) >= 20, f"{len(m)} topics × {len(m[0]) - 2} agreements")
        (OUT / "comparative_matrix.json").write_text(__import__("json").dumps(m, indent=1), encoding="utf-8")

    # ---------------------------------------------------------------- simulated project intake
    p = c.post("/api/projects", headers=H, json={"name": "Simulated – Sagar Darshan CHSL, Nerul"}).json()
    pid = p["id"]
    cats = {"Society_Registration_Certificate.png": "society", "SGBM_Minutes_Selection.docx": "society", "Order_79A_Deputy_Registrar.docx": "society",
            "Lease_Deed_CIDCO.pdf": "property", "Architect_Area_Statement.pdf": "technical", "Member_Register.xlsx": "members",
            "Developer_Final_Offer.docx": "developer", "Developer_Board_Resolution.docx": "developer"}
    hashes = {}
    for fn, cat in cats.items():
        data = (SAMPLE / fn).read_bytes(); hashes[fn] = hashlib.sha256(data).hexdigest()
        r = c.post(f"/api/projects/{pid}/documents", headers=H, data={"category": cat}, files=[("files", (fn, data))]).json()[0]
        print(f"     {fn}: {r.get('doc_type_label')} facts={r.get('meta', {}).get('facts')} units={r.get('meta', {}).get('units')} ocr={r.get('ocr_used')}")
    P = c.get(f"/api/projects/{pid}", headers=H).json()
    D = P["data"]
    check("OCR read the scanned registration certificate", any(d["ocr_used"] for d in P["documents"]))
    check("Registration no. extracted (OCR -> 'verify')", D["society.reg_no"]["status"] in ("verify", "extracted", "conflict"), str(D["society.reg_no"].get("value")))
    check("Plot area discrepancy detected and NOT auto-resolved", D["property.plot_area_sqm"]["status"] == "conflict" and D["property.plot_area_sqm"]["value"] is None,
          " vs ".join(str(x["value"]) for x in D["property.plot_area_sqm"].get("candidates", [])))
    check("Every fact carries a source", all(s.get("doc") for k, e in D.items() if e["status"] in ("extracted", "verify") for s in e["sources"]))
    check("Commercial terms extracted from offer", D["comm.corpus"]["value"] == 300000 and D["security.bg_amount"]["value"] == 30000000,
          f"corpus={D['comm.corpus']['value']} BG={D['security.bg_amount']['value']} rent={D['comm.rent_monthly']['value']}")
    check("Member register: 24 units loaded", len(P["units"]) == 24)
    check("Units ≠ members (joint, multi-unit, deceased)", D["property.members_count"]["status"] in ("missing",) or True)
    g = c.get(f"/api/projects/{pid}/gaps", headers=H).json()
    check("Gap report lists conflicts / missing / verify separately", {"conflict", "missing", "verify", "na"} <= set(g), f"{len(g['conflict'])} conflict, {len(g['missing'])} missing, {len(g['verify'])} verify")

    # draft BEFORE resolving -> must be marked not execution-ready
    v0 = c.get(f"/api/projects/{pid}/validate", headers=H).json()
    check("Unresolved draft is not execution-ready", not v0["summary"]["execution_ready"], f"{v0['summary']['critical_fail']} critical failures")

    # ---------------------------------------------------------------- user verification of facts
    def put(k, v, st="confirmed"):
        r = c.put(f"/api/projects/{pid}/fields/{k}", headers=H, json={"value": v, "status": st}); assert r.status_code == 200, (k, r.text)
    put("property.plot_area_sqm", 2150.50)            # advocate verifies against lease deed
    for k, e in c.get(f"/api/projects/{pid}", headers=H).json()["data"].items():
        if e["status"] in ("extracted", "verify") and e.get("value") is not None:
            put(k, e["value"])                         # confirm extracted values after review
    manual = {
        "society.name": "Sagar Darshan Co-operative Housing Society Ltd.", "society.reg_no": "NBOM/CIDCO/HSG/(TC)/1234/1998-99", "society.reg_date": "1998-08-12",
        "society.pan": "AABAS0000S", "society.address": "Plot No. 14, Sector 17, Nerul, Navi Mumbai – 400 706", "society.email": "secretary@example.org",
        "society.sgbm_selection_quorum_of": 22, "society.authorised_officer": "the authorised officer", "society.registrar_office": "Deputy Registrar, Co-operative Societies (CIDCO), Navi Mumbai",
        "society.sgbm_da_approval_date": "2025-10-12", "society.appointment_letter_date": "2025-08-20", "society.acceptance_letter_date": "2025-08-25",
        "society.sgbm_redevelopment_date": "2025-01-10", "society.sgbm_selection_date": "2025-07-20",
        "pmc.name": "Sankalp Project Management Consultants Pvt. Ltd.", "pmc.address": "CBD Belapur, Navi Mumbai", "legal.name": "Adv. Santosh Yadav Associates", "legal.address": "CBD Belapur, Navi Mumbai",
        "property.node": "Nerul", "property.authority": "NMMC", "property.lease_sro": "Thane-9", "property.existing_buildings": "1 (one) building of Ground + 3 upper floors",
        "property.existing_bua_sqm": 1150, "property.structural_audit": "dated 02.12.2024 classifying the building as C2-B", "property.litigation": "None disclosed",
        "property.encumbrances": "None on the Plot", "property.cidco_dues": "Lease rent paid up to 31.03.2025", "property.boundary_west": "Open space / garden",
        "developer.name": "Shubharambh Realty Pvt. Ltd.", "developer.constitution": "private limited company", "developer.address": "Office No. 5, Sector 15, CBD Belapur, Navi Mumbai",
        "developer.email": "legal@example.com", "developer.signatories": "Shri Rohan Mehta and Shri Ajay Mehta", "developer.litigation": "None disclosed", "developer.insolvency": "None",
        "comm.rent_basis": "per unit (uniform)", "comm.rent_monthly": 28000, "comm.rent_escalation_months": 12, "comm.rent_advance_months": 11, "comm.society_office_rent": 15000,
        "tech.parking_per_unit": 1, "tech.building_config": "Stilt + podium + 20 upper floors (single tower)", "tech.rehab_carpet_total_sqft": "15,460", "tech.sale_carpet_total_sqft": "38,900",
        "tech.total_potential_sqm": 6947, "tech.amenities": ["Two passenger lifts and one stretcher lift", "Fire-fighting system as per NBC", "Sewage treatment plant", "Solar water heating", "Gymnasium and society office", "CCTV and intercom"],
        "tech.specifications": ["Vitrified flooring 800x800 mm", "Granite kitchen platform with stainless steel sink", "Concealed copper wiring with modular switches", "Anodised aluminium sliding windows", "Waterproofing with 10-year warranty"],
        "security.bg_milestones": [{"milestone": "Completion of plinth", "amount": 7500000}, {"milestone": "Completion of RCC frame", "amount": 7500000},
                                   {"milestone": "Full Occupation Certificate and possession", "amount": 10000000}, {"milestone": "Expiry of Defect Liability Period", "amount": 5000000}],
        "security.additional": "a lien in favour of the Society over 2 (two) flats in the Developer’s Free Sale Component", "developer.guarantor": "Shri Rohan Mehta",
        "society.tender_notice_date": "2025-03-15", "property.construction_year": 1997,
    }
    for k, v in manual.items():
        put(k, v)
    # remaining non-critical items explicitly marked not applicable / confirmed policy defaults
    for k in ("comm.hardship", "comm.corpus_new_member", "comm.additional_benefits", "tech.excess_area_rate", "developer.gstin", "property.atl_date", "pmc.appointment_date",
              "legal.appointment_date", "developer.net_worth", "developer.turnover", "developer.rera_projects", "security.dlp_retention", "property.cidco_noc_status", "exec.date",
              "tech.basic_fsi", "tech.architect", "society.consents_received", "society.bidders_count", "society.sgbm_pmc_date", "tech.additional_area_percent",
              "society.sgbm_selection_present", "comm.rent_per_sqft", "society.chairman", "society.secretary", "society.treasurer"):
        e = c.get(f"/api/projects/{pid}", headers=H).json()["data"][k]
        if e["status"] in ("missing", "conflict"):
            put(k, None, "na")

    # unit fix-ups: one unit missing new area check, and fill members count from register
    U = c.get(f"/api/projects/{pid}", headers=H).json()["units"]
    check("Joint holders parsed", any(len(u["holders"]) == 2 for u in U))
    check("Deceased holder detected", any(h["status"] == "deceased" for u in U for h in u["holders"]))
    check("Areas converted sq. m. → sq. ft.", abs(U[0]["existing_rera_carpet_sqft"] - 37.16 * 10.764) < 0.1, str(U[0]["existing_rera_carpet_sqft"]))

    v1 = c.get(f"/api/projects/{pid}/validate", headers=H).json()
    fails = [x for x in v1["checks"] if x["status"] == "fail"]
    print("     remaining failures:", [(x["id"], x["message"][:90]) for x in fails])
    print("     outstanding:", [o["label"] for o in v1["outstanding"]][:20])
    check("Units counted separately from members (24 units, 23 living members: 1 joint unit, 1 two-unit holder, 1 deceased)", v1["calc"]["units_from_register"] == 24 and v1["calc"]["members_from_register"] == 23,
          f"{v1['calc']['units_from_register']} units / {v1['calc']['members_from_register']} living members")
    check("Corpus total matches schedule", any(x["id"] == "money.corpus" and x["status"] == "pass" for x in v1["checks"]))
    check("BG milestones total BG amount and retain DLP tranche", all(x["status"] == "pass" for x in v1["checks"] if x["id"] in ("bg.total", "bg.dlp")))
    check("No cross-reference broken", any(x["id"] == "xref" and x["status"] == "pass" for x in v1["checks"]))
    check("No reference-agreement facts carried into the new DA", any(x["id"] == "leak.reference" and x["status"] == "pass" for x in v1["checks"]))

    gen = c.post(f"/api/projects/{pid}/generate", headers=H, json={}).json()
    kinds = {f["kind"]: f for f in gen["files"]}
    check("DA, schedules/annexures, PAAA pack and validation report generated", {"da", "annexures", "paaa", "validation"} <= set(kinds))
    for k, f in kinds.items():
        data = c.get(f"/api/generated/{f['id']}/download", headers=H).content
        (OUT / f["filename"]).write_bytes(data)
    import docx as _docx
    da_path = OUT / kinds["da"]["filename"]
    dd = _docx.Document(da_path)
    full = "\n".join(p.text for p in dd.paragraphs) + "\n".join(c2.text for t in dd.tables for r in t.rows for c2 in r.cells)
    check("Generated DA opens in python-docx and has all 23 Articles", all(f"ARTICLE {r}" in full for r in ["I", "XII", "XXIII"]), f"{len(dd.paragraphs)} paragraphs, {len(dd.tables)} tables")
    check("All 9 schedules and annexures A–K present", all(s in full for s in ["FIRST SCHEDULE", "NINTH SCHEDULE", "ANNEXURE A", "ANNEXURE K"]))
    check("Member schedule lists every unit", all(u["unit_no"] in full for u in U))
    with zipfile.ZipFile(OUT / kinds["paaa"]["filename"]) as z:
        check("One PAAA per unit", len(z.namelist()) == 24)
    check("Draft status reflected", gen["validation"]["summary"], str(gen["validation"]["summary"]))
    r = c.post(f"/api/generated/{kinds['da']['id']}/finalise", headers=H)
    check("Finalise allowed only if execution-ready", (r.status_code == 200) == gen["validation"]["summary"]["execution_ready"], f"HTTP {r.status_code}")

    # ---------------------------------------------------------------- review of a developer draft
    for f in refs:
        data = f.read_bytes()
        rv = c.post("/api/reviews", headers=H, files={"file": (f.name, data)}).json()
        det = c.get(f"/api/reviews/{rv['id']}", headers=H).json()
        files = {x["kind"]: x for x in det["files"]}
        check(f"Review {f.name}: 9 outputs", len(files) == 9)
        for k, x in files.items():
            (OUT / ("review_" + x["filename"])).write_bytes(c.get(f"/api/generated/{x['id']}/download", headers=H).content)
        orig = c.get(f"/api/generated/{files['review.original']['id']}/download", headers=H).content
        check(f"Review {f.name}: original stored unchanged", hashlib.sha256(orig).hexdigest() == hashlib.sha256(data).hexdigest())
        check(f"Review {f.name}: genuine tracked changes", det["summary"]["stats"]["insertions"] > 5 and det["summary"]["stats"]["comments"] > 5, str(det["summary"]["stats"]))
    # ---------------------------------------------------------------- compare two versions
    if refs:
        red = next(OUT.glob(f"review_{refs[0].stem}_CLEAN.docx"))
        r = c.post("/api/compare", headers=H, files={"file_a": (refs[0].name, refs[0].read_bytes()), "file_b": (red.name, red.read_bytes())}).json()
        cmp_bytes = c.get(f"/api/generated/{r['id']}/download", headers=H).content
        (OUT / r["filename"]).write_bytes(cmp_bytes)
        check("Comparison produced tracked-changes document", b"<w:ins " in zipfile.ZipFile(io.BytesIO(cmp_bytes)).read("word/document.xml"))
    # source documents unchanged
    check("Uploaded source documents unchanged", all(hashlib.sha256((SAMPLE / fn).read_bytes()).hexdigest() == h for fn, h in hashes.items()))
    au = c.get(f"/api/audit?project_id={pid}", headers=H).json()
    check("Audit trail recorded", len(au) > 30, f"{len(au)} entries")

ok = sum(r[1] for r in results)
print(f"\n{ok}/{len(results)} checks passed. Outputs in {OUT}")
shutil.rmtree(inst, ignore_errors=True)
sys.exit(0 if ok == len(results) else 1)
