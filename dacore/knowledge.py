"""Legal knowledge base: clause library, reference-agreement ingestion, search, legal register, comparative matrix."""
from __future__ import annotations

import math
import re
from collections import Counter

from sqlalchemy.orm import Session

from .db import Clause, LegalSource
from .drafting.master_da import ARTICLES, C
from .review.rules import MISSING, RULES

TOPICS = {
    "definitions": r"shall mean|means and includes|definition",
    "appointment": r"appoint\w* (?:the )?developer|79\s*\(?A\)?|tender|selection",
    "development_rights": r"development rights|grant of|licen[cs]e to enter|part performance|53A",
    "fsi": r"\bFSI\b|floor space|TDR|fungible|premium|development potential|amalgamat",
    "entitlement": r"carpet area|new flat|permanent alternate|PAAA|members.{0,5}new premises|allocation|parking",
    "rent": r"\brent\b|displacement compensation|transit|temporary (?:alternate )?accommodation",
    "monetary": r"corpus|brokerage|shifting|hardship|deposit",
    "bank_guarantee": r"bank guarantee",
    "developer_reps": r"developer represents|financial (?:strength|capacity)|insolven|blacklist",
    "society_reps": r"society represents|society (?:hereby )?declares|title|encumbrance",
    "developer_obligations": r"developer shall (?:at its own cost|obtain|construct|demolish|bear)|labour|contractor|safety",
    "society_obligations": r"society shall (?:sign|cause|co-?operate|not)|members shall vacate",
    "vacation": r"vacat|handover date|vacant possession",
    "completion": r"complet\w+|commencement certificate|occupa\w+ certificate|grace period",
    "force_majeure": r"force majeure|act of god|pandemic",
    "defects": r"defect|seepage|leakage|warrant|maintenance contract",
    "possession": r"possession notice|possession date|possession of the (?:new|members)",
    "free_sale": r"free sale|sale premises|purchaser|agreement for sale|developer.{0,5}s allocation",
    "rera": r"\bRERA\b|real estate \(regulation|promoter",
    "tax": r"\bGST\b|stamp duty|registration charges|income tax|TDS",
    "ld": r"liquidated damages|penalty",
    "termination": r"terminat",
    "indemnity": r"indemn",
    "insurance": r"insurance",
    "arbitration": r"arbitrat|dispute",
    "assignment": r"assign|change (?:in|of) control|shareholding",
    "mortgage": r"mortgage|charge|lien|finance",
    "poa": r"power of attorney",
    "notices": r"notice[s]? .{0,40}(?:in writing|address)",
    "misc": r"severab|waive|entire agreement|counterpart|confidential",
}

FACT_MARKERS = re.compile(r"Rs\.?\s*[\d,]{4,}|₹\s*[\d,]{4,}|\b[A-Z]{5}\d{4}[A-Z]\b|Plot\s*No\.?\s*[\w/]+|\b\d{1,2}(?:st|nd|rd|th)\s+\w+,?\s+20\d\d|Sector\s*[-–]?\s*\d+|\b(?:Shri|Smt|Mr|Mrs)\.?\s+[A-Z][a-z]+", re.I)


def topic_of(text: str) -> str:
    best, n = "general", 0
    for t, rx in TOPICS.items():
        k = len(re.findall(rx, text, re.I))
        if k > n:
            best, n = t, k
    return best


def _plain(text: str) -> str:
    text = re.sub(r"\{\{(?:\w+:)?([\w.]+)\}\}", lambda m: "[●]", text)
    return re.sub(r"\[\[(?:ref|art|sch|ann):([\w.]+)\]\]", lambda m: f"[{m.group(1)}]", text)


def _walk(cl: C):
    yield cl
    for s in cl.sub:
        yield from _walk(s)


def seed_library(db: Session) -> int:
    if db.query(Clause).filter(Clause.source_agreement == "Master DA (consolidated framework)").count():
        return 0
    n = 0
    for art in ARTICLES:
        for top in art.clauses:
            for cl in _walk(top):
                if not cl.lib:
                    continue
                L = cl.lib
                full = _plain(cl.text + (" " + " ".join(s.text for s in cl.sub) if cl.sub else ""))
                db.add(Clause(clause_code=f"MDA-{cl.id}", subject=L.subject, article=f"Article {art.num} – {art.title}",
                              standard_wording=full, society_favourable=full, neutral_version=_plain(L.neutral) if L.neutral else "",
                              alternative_wording=_plain(L.neutral) if L.neutral else "",
                              source_agreement="Master DA (consolidated framework)", legal_provision=L.provision, explanation=L.explain,
                              risk_addressed=L.risk, recommended_use="Default clause in generated Development Agreements.",
                              classification=L.classification, approval_status="approved", topic=topic_of(full)))
                n += 1
    for r in RULES:
        db.add(Clause(clause_code=f"RVW-{r.id}", subject=r.title, article="Review rule",
                      standard_wording=r.text, society_favourable=r.text, source_agreement="Review rule library",
                      legal_provision=r.legal, explanation=r.reason, risk_addressed=r.risk,
                      recommended_use=f"Applied by the reviewer when a draft contains: /{r.pattern[:120]}/",
                      classification="Critical Society protection" if r.severity == "Critical" else ("Negotiable" if not r.mandatory else "Preferred"),
                      approval_status="approved", topic=topic_of(r.title + " " + r.reason)))
        n += 1
    for m in MISSING:
        db.add(Clause(clause_code=f"MIS-{m.id}", subject=m.title, article="Missing-clause insert", standard_wording=m.text,
                      society_favourable=m.text, source_agreement="Review rule library", explanation=m.reason, risk_addressed=m.risk,
                      recommended_use="Inserted by the reviewer when the draft has no equivalent provision.",
                      classification="Critical Society protection" if m.severity == "Critical" else "Preferred", approval_status="approved",
                      topic=topic_of(m.title + " " + m.text)))
        n += 1
    db.commit()
    return n


def ingest_reference(db: Session, name: str, texts: list[str]) -> dict:
    """Split a reference agreement into candidate clauses (status pending_review – never auto-approved)."""
    from .review.reviewer import _clause_refs
    refs = _clause_refs(texts)
    prefix = re.sub(r"[^A-Z0-9]", "", name.upper())[:10] or "REF"
    existing = db.query(Clause).filter(Clause.source_agreement == name).count()
    if existing:
        return {"added": 0, "skipped": existing}
    added, flagged = 0, 0
    rx_rules = [(r, re.compile(r.pattern, re.I | re.M)) for r in RULES]
    for i, t in enumerate(texts):
        t = t.strip()
        if len(t) < 140 or t.startswith("|") or " | " in t[:80]:
            continue
        hits = [r.id for r, rx in rx_rules if rx.search(t) and not (r.guard and re.search(r.guard, t, re.I))]
        facts = bool(FACT_MARKERS.search(t))
        flagged += facts
        db.add(Clause(clause_code=f"{prefix}-{i:04d}", subject=t[:90] + ("…" if len(t) > 90 else ""), article=refs[i] if i < len(refs) else "",
                      standard_wording=t, source_agreement=name,
                      explanation=("Flagged by review rules: " + ", ".join(hits)) if hits else "No review rule triggered.",
                      classification="Not recommended" if hits else "Acceptable alternative",
                      approval_status="pending_review", contains_project_facts=facts, topic=topic_of(t)))
        added += 1
    db.commit()
    return {"added": added, "with_project_facts": flagged}


# ------------------------------------------------------------------ search (BM25)
def _tok(s: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9]+", (s or "").lower()) if len(w) > 2]


def search(db: Session, q: str, topic: str | None = None, status: str | None = None, classification: str | None = None, limit=50) -> list[Clause]:
    qs = db.query(Clause)
    if topic:
        qs = qs.filter(Clause.topic == topic)
    if status:
        qs = qs.filter(Clause.approval_status == status)
    if classification:
        qs = qs.filter(Clause.classification == classification)
    rows = qs.all()
    if not q:
        return rows[:limit]
    docs = [_tok(" ".join([r.subject, r.standard_wording, r.explanation, r.risk_addressed, r.legal_provision])) for r in rows]
    N = len(docs) or 1
    avg = sum(map(len, docs)) / N if docs else 1
    df = Counter(w for d in docs for w in set(d))
    qt = _tok(q)
    scored = []
    for r, d in zip(rows, docs):
        tf = Counter(d)
        s = 0.0
        for w in qt:
            if w in tf:
                idf = math.log(1 + (N - df[w] + 0.5) / (df[w] + 0.5))
                s += idf * tf[w] * 2.2 / (tf[w] + 1.2 * (0.25 + 0.75 * len(d) / avg))
        if s > 0:
            scored.append((s + (0.5 if r.approval_status == "approved" else 0), r))
    scored.sort(key=lambda x: -x[0])
    return [r for _s, r in scored[:limit]]


# ------------------------------------------------------------------ comparative matrix
MATRIX_TOPICS = [
    ("Bank guarantee timing (before vacation)", r"bank guarantee", ["BG-01", "BG-05"], "VII / XII"),
    ("BG release verified by PMC", r"bank guarantee[^.]{0,200}release|released? .{0,40}stage", ["BG-02"], "VII"),
    ("Vacation conditions precedent", r"vacat", ["BG-05", "MC-02"], "XII"),
    ("Rent until actual possession", r"\brent\b", ["RENT-01", "RENT-02", "POS-01"], "VI"),
    ("Rent during force majeure", r"force majeure", ["FM-05", "MC-13"], "XIV"),
    ("Narrow force majeure", r"force majeure", ["FM-01", "FM-02", "FM-03", "FM-04"], "XIV"),
    ("Completion = Full OC", r"occupa\w+ certificate", ["POS-02", "POS-04", "POS-05", "DEL-01"], "XIII"),
    ("Long-stop & replacement developer", r"terminat", ["MC-03"], "XIII / XXI"),
    ("Termination grounds", r"terminat", ["TER-01", "TER-02", "TER-04", "TER-07", "TER-09"], "XXI"),
    ("No automatic reimbursement on termination", r"terminat", ["TER-06"], "XXI"),
    ("Arbitration not a bar", r"arbitrat", ["TER-05", "TER-10"], "XXIII"),
    ("Developer indemnity (no caps)", r"indemn", ["IND-01", "IND-02", "IND-03", "IND-07"], "XXII"),
    ("Society indemnity limited", r"indemn", ["IND-04", "IND-05", "IND-06"], "XXII"),
    ("No mortgage of rehab / plot", r"mortgage", ["FIN-01", "MC-14"], "X"),
    ("Assignment / change of control", r"assign", ["MC-04"], "XXIII"),
    ("Society approval of design changes", r"plan|design|amenit", ["DIS-01", "DIS-03", "DIS-04", "DIS-05"], "X"),
    ("Defect liability (statutory floor)", r"defect", ["DLP-01", "DLP-02", "MC-10"], "XV"),
    ("Carpet area shortfall", r"carpet", ["MC-07"], "V"),
    ("Liquidated damages", r"liquidated damages|penalty", ["DEL-04"], "XX"),
    ("Proportionate remedies vs members", r"non.?consent|non.?cooperat|fail(?:s|ing)? to vacate", ["MEM-01", "MEM-02"], "XII"),
    ("Formal consents / amendments", r"amend|representative", ["REP-01", "AMD-01"], "XI / XXIII"),
    ("Licence co-terminus", r"licen[cs]e", ["LIC-01", "LIC-02"], "III"),
    ("RERA allocation", r"\bRERA\b", ["RERA-01"], "XVIII"),
    ("Insurance", r"insurance", ["MC-05"], "XXII"),
    ("Quality / third-party testing", r"quality|test", ["MC-06"], "X"),
]


def comparative_matrix(ref_results: dict[str, tuple[list[str], list[dict]]]) -> list[dict]:
    """ref_results: name -> (paragraph texts, review findings dicts)."""
    rows = []
    for title, present_rx, rule_ids, art in MATRIX_TOPICS:
        row = {"topic": title, "master": f"Society-protective standard – Article {art}"}
        for name, (texts, findings) in ref_results.items():
            full = "\n".join(texts)
            hits = [f for f in findings if f["rule"] in rule_ids]
            if not re.search(present_rx, full, re.I) or any(f["kind"] == "insertion" for f in hits):
                pos = "Absent"
            elif hits:
                pos = "Present – deficient (" + ", ".join(sorted({f['rule'] for f in hits})) + ")"
            else:
                pos = "Present – adequate"
            row[name] = pos
        rows.append(row)
    return rows


# ------------------------------------------------------------------ legal register
REGISTER = [
    ("MCS-79A", "Maharashtra Co-operative Societies Act, 1960", "statute", "Section 79A", "Power of the State Government to issue directions to societies in public interest; the redevelopment directions are issued under this section.", ["appointment", "vacation"]),
    ("GOV-79A-2019", "Directions under Section 79A for redevelopment of co-operative housing societies", "circular", "Order dated 4 July 2019 (as cited in the reference agreements)", "Procedure for redevelopment: general body resolutions, PMC appointment, tender, selection of developer in SGBM in the presence of the authorised officer. Verify the current version and any later amendments.", ["appointment"]),
    ("MCS-91", "Maharashtra Co-operative Societies Act, 1960", "statute", "Section 91", "Disputes touching the business of a society between the society and its members are referred to the Co-operative Court.", ["arbitration"]),
    ("RERA-2K", "Real Estate (Regulation and Development) Act, 2016", "statute", "Section 2(k)", "Definition of carpet area (net usable floor area excluding external walls, service shafts, exclusive balcony/verandah and exclusive open terrace, including internal partition walls).", ["entitlement"]),
    ("RERA-2ZK", "Real Estate (Regulation and Development) Act, 2016", "statute", "Section 2(zk)", "Definition of promoter; whether a society granting development rights is a promoter / co-promoter must be examined on the facts and MahaRERA orders.", ["rera"]),
    ("RERA-3", "Real Estate (Regulation and Development) Act, 2016", "statute", "Section 3", "Prior registration of real estate projects before advertisement or sale.", ["rera", "free_sale"]),
    ("RERA-4-2-L-D", "Real Estate (Regulation and Development) Act, 2016", "statute", "Section 4(2)(l)(D)", "Seventy per cent of amounts realised from allottees to be deposited in a separate account and used only for construction and land cost of that project.", ["rera"]),
    ("RERA-11", "Real Estate (Regulation and Development) Act, 2016", "statute", "Section 11", "Functions and duties of the promoter, including obtaining completion / occupancy certificate and handing over documents to the association of allottees.", ["rera", "possession"]),
    ("RERA-14", "Real Estate (Regulation and Development) Act, 2016", "statute", "Section 14", "Adherence to sanctioned plans; restrictions on alterations without consent; Section 14(3): structural defect / workmanship defect liability for five years from possession.", ["defects", "developer_obligations"]),
    ("RERA-18", "Real Estate (Regulation and Development) Act, 2016", "statute", "Section 18", "Return of amount and compensation where the promoter fails to complete or give possession in accordance with the agreement.", ["completion", "ld"]),
    ("RERA-19-10", "Real Estate (Regulation and Development) Act, 2016", "statute", "Section 19(10)", "Allottee to take physical possession within two months of the occupancy certificate.", ["possession"]),
    ("ICA-32-56", "Indian Contract Act, 1872", "statute", "Sections 32 and 56", "Contingent contracts and frustration; relevant to the construction of force majeure clauses.", ["force_majeure"]),
    ("ICA-73-74", "Indian Contract Act, 1872", "statute", "Sections 73 and 74", "Compensation for breach; stipulated damages limited to reasonable compensation not exceeding the amount named – relevant to LD and penalties on members.", ["ld", "termination"]),
    ("ICA-124-126", "Indian Contract Act, 1872", "statute", "Sections 124–126", "Contracts of indemnity and guarantee.", ["indemnity", "bank_guarantee"]),
    ("ICA-202", "Indian Contract Act, 1872", "statute", "Section 202", "Agency coupled with interest not terminable to the prejudice of that interest – relevant to ‘irrevocable’ powers of attorney.", ["poa"]),
    ("TPA-53A", "Transfer of Property Act, 1882", "statute", "Section 53A", "Part performance; DA should clarify that possession to the developer is not in part performance.", ["development_rights"]),
    ("TPA-10", "Transfer of Property Act, 1882", "statute", "Section 10", "Conditions absolutely restraining alienation are void – relevant to bars on members transferring their flats.", ["society_obligations"]),
    ("TPA-58", "Transfer of Property Act, 1882", "statute", "Section 58", "Mortgage defined – relevant to restrictions on developer financing.", ["mortgage"]),
    ("REG-17", "Registration Act, 1908", "statute", "Section 17", "Documents compulsorily registrable; DA, POA and PAAA registration requirements to be confirmed.", ["tax"]),
    ("MSA-4", "Maharashtra Stamp Act, 1958", "statute", "Section 4", "Several instruments – stamp duty on the principal instrument; ancillary instruments (e.g. PAAA) – verify current treatment.", ["tax"]),
    ("MSA-ART5", "Maharashtra Stamp Act, 1958", "statute", "Schedule I, Article 5 (agreements – development agreements)", "Stamp duty on development agreements; verify the current rate and the treatment of redevelopment by co-operative societies.", ["tax"]),
    ("ACA-9", "Arbitration and Conciliation Act, 1996", "statute", "Section 9", "Interim measures by court before, during or after arbitral proceedings.", ["arbitration", "termination"]),
    ("ACA-11-12", "Arbitration and Conciliation Act, 1996", "statute", "Sections 11 and 12 (with the Seventh Schedule)", "Appointment of arbitrators; independence and impartiality – unilateral appointment by one party is open to challenge.", ["arbitration"]),
    ("ACA-29A", "Arbitration and Conciliation Act, 1996", "statute", "Section 29A", "Time limit for arbitral award.", ["arbitration"]),
    ("IEA-52-60", "Indian Easements Act, 1882", "statute", "Sections 52 and 60", "Licence defined; when a licence is revocable.", ["development_rights"]),
    ("MRTP-113", "Maharashtra Regional and Town Planning Act, 1966", "statute", "Section 113", "Designation of the new town development authority (CIDCO for Navi Mumbai).", ["definitions"]),
    ("UDCPR-2020", "Unified Development Control and Promotion Regulations for Maharashtra", "regulation", "Redevelopment / incentive FSI provisions", "Applicable development control regulations for NMMC / PMC areas; specific regulations and incentive FSI to be verified on the current consolidated text.", ["fsi"]),
    ("ITA-194IC", "Income-tax Act, 1961", "statute", "Section 194-IC", "TDS on monetary consideration under a specified agreement (joint development) – applicability to redevelopment payments to be verified by tax advisor.", ["tax"]),
    ("GST-REDEV", "CGST Act, 2017 and rate notifications", "statute", "Taxation of development rights / construction of rehabilitation premises", "GST treatment of development rights and construction for existing members to be confirmed against current notifications. No specific notification is recorded here to avoid citing an unverified version.", ["tax"]),
    ("CIDCO-NOC", "CIDCO policy on redevelopment of CIDCO-leased properties", "circular", "Redevelopment NOC / transfer and lease conditions", "CIDCO no-objection for redevelopment and conditions of the lease deed – obtain and record the applicable current policy document for each project.", ["fsi", "appointment"]),
    ("CASELAW", "Judgments", "judgment", "—", "No judgments are pre-loaded. Add judgments only after the advocate has read and verified them (citation, court, date, proposition).", []),
]


def seed_register(db: Session) -> int:
    if db.query(LegalSource).count():
        return 0
    for code, title, kind, prov, prop, topics in REGISTER:
        db.add(LegalSource(code=code, title=title, kind=kind, provision=prov, proposition=prop, topics=topics,
                           source_ref="Bare Act / official gazette text to be attached", effective_version="As amended – verify",
                           verification_status="advocate verification required"))
    db.commit()
    return len(REGISTER)
