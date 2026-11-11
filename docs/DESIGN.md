# Design notes – Redevelopment DA Suite

## 1. Reference agreements analysed

Two of the six intended reference agreements were provided and analysed in full:

| Agreement | Character | Use in the framework |
|---|---|---|
| **Preetisangam CHSL × developer (S6 draft for finalisation)** | Society-side draft; 23 Articles + 12 Schedules; good recital structure, definitions in a schedule, member-wise schedules, staged BG release, waiver clause, liability carve-outs. | **Principal structural model** (recitals → definitions → purpose → appointment → entitlement → consideration → developer rights → representations → obligations → completion → termination → miscellaneous → schedules). |
| **Nivara CHSL (developer draft, Oct 2026)** | Developer-favourable: termination only for non-payment of rent and only through arbitration; Society barred from terminating before an award; full refund of developer investment before any new developer; deemed possession; completion deemed on OC application; broad force majeure (material shortage, rule changes, “directly or indirectly”); per-day penalties with 24% interest on members; indemnity capped and limited to “sole” negligence; irrevocable licence. | Source of **review rules** (what to correct) and a test case for the reviewer. |

Anmol, Satya (track changes), Citadel and Kohinoor were **not** provided. The ingestion pipeline (Reference
Agreements screen) accepts them at any time; their clauses enter the library as *pending review* and the
comparative matrix gains a column automatically.

No names, amounts, plot details or other facts from the references are used in the template. The validator
fails a draft if reference-specific markers appear in it.

## 2. Comparative clause matrix (from the analysis)

| Protection | Preetisangam | Nivara | Master DA |
|---|---|---|---|
| BG furnished before vacation | Not tied to vacation sequence | 50% at CC, 50% *after* handover of all units | Art. VII – condition precedent to Vacation Notice |
| BG release verification | Stages; no certifier named | Developer's own architect | PMC certificate; DLP tranche retained |
| Vacation conditions precedent | Registration notice / vacating notice after CC | CC applied for *after* vacation | Art. XII – 7 sequential CPs, PMC-certified |
| Rent cessation | Possession date / 30 days from Possession Notice (after full OC) – adequate | Till PAA possession after OC – adequate | Possession Date tied to *Valid* Possession Notice |
| Rent during force majeure | Not preserved (obligations “excused”) | Preserved | Art. XIV – expressly continues |
| Force majeure scope | Broad catch-all | Broad (materials, rule changes, “directly or indirectly”) | Narrow, objective, with exclusions, notice and proof |
| Completion = full OC | Yes | Deemed on OC application / architect | Full OC + utilities + amenities + PMC |
| Long-stop / replacement developer | New developer on termination | Barred until refund of investment | Long-Stop Date; Society appoints new developer |
| Termination grounds | 4 grounds; 90-day cure; “non-disputable” qualifier | Rent default only; via arbitration | 9 Developer Events of Default; cure; no award needed |
| Consequences of termination | Society not liable – good | Refund everything, irrespective of fault | Fault-based; payment only from new developer, PMC-certified |
| Developer indemnity | Broad, but contradicted by limitation clause | Capped; “solely negligent”; ends at handover | Uncapped, survives, covers statutory/labour/RERA/tax |
| Society indemnity | Includes title “as investigated by the Developer”; CIDCO NOC | Includes loss of profit, holding costs | Knowledge-qualified, disclosure schedule, direct loss only |
| Mortgage of rehab / plot | Excluded – adequate | Excluded – adequate | Excluded; lender acknowledgement required |
| Assignment / change of control | 51% shareholding retained – adequate | Not restricted for Developer | GB approval; 51% control test |
| Design changes | Some unrestricted authority | “Exclusive and unfettered” | GB approval for anything affecting rehab/common areas; RERA s.14 |
| Defect liability | 5 years; self-help with RCC consultant – good | Void on alterations; narrow “defect” | RERA floor; independent inspection; self-help; AMCs |
| Remedies against members | 6 months' rent + 100% corpus per month + 18% | Rs 50,000/day + 24% | Documented costs; no rent for delay period |
| Consents / amendments | Single representative binding; amendments by minutes | — | Two signatories + GB resolution; amendments only by GB |
| RERA allocation | Co-promoter limited to title – good; Society solely liable for litigation delays | Developer solely liable – good | Developer is promoter; Society's liability confined to title |

The same comparison is produced automatically (rule-based) by **Reference Agreements → Comparative clause matrix**.

## 3. Master DA structure

Articles I–XXIII exactly as specified in the brief (definitions → miscellaneous), followed by:

* Schedules: First (Plot), Second (Existing buildings), Third (member-wise area entitlement), Fourth
  (rehabilitation & parking allocation), Fifth (member-wise financials), Sixth (amenities & specifications),
  Seventh (BG schedule), Eighth (completion schedule), Ninth (disclosures: litigation, encumbrances, mortgages,
  pending transmission, developer disclosures).
* Annexures A–K: SGBM resolution, board resolution, registration certificate, 79A order, Accepted Offer
  (copies, auto-linked to uploaded documents), and generated formats of the Bank Guarantee, PAAA, Vacation
  Undertaking, Power of Attorney and Handover Memorandum / Possession Receipt, plus plans & area statement.

Numbering and every cross-reference (`[[ref:…]]`, `[[art:…]]`, `[[sch:…]]`, `[[ann:…]]`) are resolved at render
time, so conditional clauses never leave a gap or a dangling reference.

## 4. Architecture

```
 Browser (web/ – vanilla JS SPA)
        │ REST/JSON + multipart
 FastAPI (dacore/api.py) ── RBAC (security.py) ── audit log
        │
 services.py ── workflows
   ├─ ingest.py      DOCX / PDF / OCR (RapidOCR, on-device) / XLSX / images → segments with page & paragraph
   ├─ extract.py     rule extractors + member-register parser + consolidation (conflicts never auto-resolved)
   ├─ ai.py          optional Claude (structured outputs; quotes verified against source text)
   ├─ drafting/      master_da.py + annexure_texts.py → render.py (document model) → docx_builder.py (.docx)
   ├─ validation.py  Module 5 checks; gate for finalisation
   ├─ review/        rules.py → reviewer.py (reasonableness test) → redline.py (w:ins / w:del / comments) → reports.py
   └─ knowledge.py   clause library, reference ingestion, BM25 search, comparative matrix, legal register
        │
 SQLAlchemy → SQLite (default) or PostgreSQL ;  encrypted file store (Fernet) for uploads and outputs
```

### Deviations from the preferred stack (and why)

* **Frontend**: Node.js is not installed on the build machine, so the interface is a no-build vanilla JS
  single-page app served by FastAPI. The API is framework-agnostic; a Next.js front end can be added later
  against the same endpoints.
* **Database**: SQLite by default; PostgreSQL by `DATABASE_URL` (SQLAlchemy models are portable).
* **Vector database**: clause retrieval uses BM25 keyword ranking over the clause library (no external
  service). An embedding index can be added behind `knowledge.search` without changing callers.
* **OCR**: RapidOCR (ONNX, pip-installable, runs locally) instead of Tesseract (not installed).

### Track-changes engine (review/redline.py)

* Paragraph text is mapped to run-level character offsets; only runs that are direct children of a paragraph
  are edited. Runs are split at edit boundaries with their `rPr` preserved.
* Deleted runs are wrapped in `<w:del>` with `<w:delText>`; replacement text is a new run (cloned `rPr`)
  inside `<w:ins>`; each carries `w:id`, `w:author`, `w:date`.
* New clauses are new paragraphs cloning the anchor's `pPr` (keeping numbering) with a tracked paragraph
  mark; manually numbered clauses get an “A” suffix (e.g. 12.5A) so existing numbering is not disturbed.
* Comments go to `word/comments.xml` (created or appended) with range start/end and reference runs; the
  relationship and content-type entries are added when needed.
* Text inside existing revisions, fields or hyperlinks is locked; edits there are refused and reported rather
  than risking a corrupt file.
* The clean copy is produced by accepting all revisions in XML (and removing comments).
* Outputs were checked with the OOXML XSD validator and the redlining validator (every change by the review
  author is tracked) for both reference agreements.

### Reasonableness test (reviewer.reasonable)

An amendment is not applied automatically if it would delete a beneficial provision, or would introduce
figures not already in the paragraph (figures to be agreed are written as `[●]` and marked *negotiable*).
Rules carry guards so satisfactory clauses are left untouched; comment-only rules raise negotiation points
without altering text.

## 5. Known limitations

* Extraction rules are tuned to typical Navi Mumbai documents; unusual layouts may need rules added or the
  Claude extractor enabled. Every extracted value must be confirmed by a user before it is treated as verified.
* `.doc` (legacy) and PDF agreements must be converted to `.docx` before a Track Changes review.
* The output has not been opened in Microsoft Word on this machine (Word is not installed). It was checked
  against the OOXML schemas and re-opened programmatically. Before relying on the files, open them once in Word.
* The legal register is a starting point; no entry is marked verified, and no judgments are pre-loaded.
