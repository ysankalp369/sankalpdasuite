# Redevelopment DA Suite

Society-side Development Agreement generator and reviewer for co-operative housing society
redevelopment in Maharashtra (Navi Mumbai · CIDCO leasehold · NMMC / Panvel · UDCPR · MahaRERA).
Built for Adv. Santosh Yadav Associates (legal) and Sankalp Project Management Consultants Pvt. Ltd. (PMC).

## Run

```bash
python -m venv C:\Users\<you>\.venvs\da-suite      # keep the venv on a SHORT path (Windows DLL path limit)
C:\Users\<you>\.venvs\da-suite\Scripts\python -m pip install -r requirements.txt
C:\Users\<you>\.venvs\da-suite\Scripts\python run.py            # http://127.0.0.1:8765
```

On first start a Super Administrator is created; its password is written to
`instance/initial_admin_credentials.txt`. Sign in, change the password, then create users for each role.

Optional settings (environment variables):

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | PostgreSQL, e.g. `postgresql+psycopg://user:pass@host/dasuite` (default: SQLite in `instance/`) |
| `ANTHROPIC_API_KEY` | Enables Claude-assisted extraction, review suggestions and register-bound legal Q&A |
| `DA_AI_ENABLED` | `auto` (default) / `on` / `off` |
| `DA_STORAGE_KEY` | Fernet key for encrypting stored documents (default: generated into `instance/storage.key`) |
| `DA_REVIEW_AUTHOR` | Author name shown on tracked changes and comments (default `SYA Legal Review`) |

## What it does

**Module 1 – DA generator.** Upload society, property, member, developer and technical documents
(PDF, DOCX, XLSX/CSV, scanned PDF and images through on-device OCR). Each document is classified, facts
are extracted with document / page / paragraph references, and the member register becomes unit rows
with holder lists (units and members are never assumed equal). Contradictory values (e.g. plot area in
the lease deed vs the architect's statement) become **conflicts** that a user must resolve. The master
DA (23 Articles, 9 Schedules, Annexures A–K) is then rendered with every outstanding item marked `[●]`
in yellow and every unverified value in turquoise. Outputs: DA (.docx), schedules & annexures, a
member-wise PAAA pack (.zip) and a validation report.

**Module 2 – Reviewer.** Upload any DA (.docx). About 60 targeted society-protective rules and 14
missing-clause checks run under a reasonableness test (no new facts or figures, which are entered as `[●]` and
marked negotiable; no deletion of beneficial provisions; satisfactory clauses retained). Outputs:
original (unchanged, SHA-256 recorded), **redline with genuine Word revisions (`w:ins`/`w:del`) and
comments**, clean revised copy, Legal Review Report, Missing Clauses Report, Society Risk Matrix (.xlsx),
Clause Comparison, Negotiation Report and Execution Checklist.

**Module 3 – Knowledge.** Clause library (master clauses, review rules, missing-clause inserts and
clauses ingested from reference agreements). Ingested clauses are always *pending review*; clauses
containing project facts cannot be approved until made generic. BM25 search. Comparative matrix across
all ingested references. Legal register of statutes/circulars, every entry “advocate verification
required” until marked verified with its source; no judgments are pre-loaded.

**Module 5 – Validation.** Definitions, capitalisation, cross-references, schedules/annexures, units vs
members, missing areas, area reductions, corpus and rent totals, BG milestones vs BG amount and DLP
retention, date chronology, rent/completion/FM/termination consistency, critical blanks, conflicts,
unverified facts and leakage of reference-agreement facts. A DA cannot be *finalised* while any
critical check fails.

**Roles.** Super Administrator, Advocate / Legal Head, Junior Advocate, PMC Administrator, Project
Engineer, Document Manager. Only the Legal Head / Super Admin can approve clauses and finalise drafts.
Every upload, edit, approval, generation and download is in the audit trail. Stored documents and
outputs are encrypted at rest.

## Tests

```bash
python tests/make_sample_project.py tests/sample_project      # fictitious society for testing
python tests/test_end_to_end.py <folder-with-reference-DAs.docx>
```

## Layout

```
dacore/            core engines
  schema.py        project field registry (status: confirmed/extracted/verify/conflict/missing/na)
  ingest.py        readers, OCR, classification
  extract.py       fact rules, member-register parser, consolidation & conflict detection
  drafting/        master_da.py (template), annexure_texts.py, render.py, docx_builder.py
  validation.py    Module 5 checks
  review/          redline.py (OOXML track changes), rules.py, reviewer.py, reports.py
  knowledge.py     clause library, reference ingestion, search, matrix, legal register
  ai.py            optional Claude integration (structured outputs, quote-verified)
  services.py      workflows      api.py  FastAPI routes      security.py  auth, RBAC, encryption, audit
web/               single-page interface (no build step)
tests/             simulated project + end-to-end test
docs/DESIGN.md     analysis, clause matrix, architecture
```

## Important

Generated documents are drafts for detailed advocate review. Project facts, applicable law, stamp duty
and statutory requirements must be verified before execution and registration.
