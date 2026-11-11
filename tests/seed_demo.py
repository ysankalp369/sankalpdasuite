"""Load demo data into the local instance: reference agreements, the simulated project and one review.

usage: python tests/seed_demo.py <folder-with-reference-DAs.docx>
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from dacore import knowledge, services  # noqa: E402
from dacore.db import Project, SessionLocal, User, init_db  # noqa: E402

init_db()
db = SessionLocal()
knowledge.seed_library(db); knowledge.seed_register(db)
admin = db.query(User).filter_by(role="super_admin").first()
refs = sorted(Path(sys.argv[1]).glob("*.docx")) if len(sys.argv) > 1 else []
for f in refs:
    print("reference", f.name, services.ingest_reference_agreement(db, admin, f.name, f.read_bytes()))
if not db.query(Project).filter_by(name="Simulated – Sagar Darshan CHSL, Nerul").first():
    p = services.create_project(db, admin, "Simulated – Sagar Darshan CHSL, Nerul")
    cats = {"Society_Registration_Certificate.png": "society", "SGBM_Minutes_Selection.docx": "society", "Order_79A_Deputy_Registrar.docx": "society",
            "Lease_Deed_CIDCO.pdf": "property", "Architect_Area_Statement.pdf": "technical", "Member_Register.xlsx": "members",
            "Developer_Final_Offer.docx": "developer", "Developer_Board_Resolution.docx": "developer"}
    for fn, cat in cats.items():
        services.ingest_document(db, admin, p, fn, (ROOT / "tests" / "sample_project" / fn).read_bytes(), cat)
    print("project", p.id, services.gaps(p)["conflict"][0]["label"] if services.gaps(p)["conflict"] else "")
for f in refs[:1]:
    rv = services.run_review(db, admin, f.name, f.read_bytes())
    print("review", rv.id, rv.summary["counts"])
