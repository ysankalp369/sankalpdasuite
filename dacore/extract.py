"""Fact extraction (rule engine + optional Claude) and consolidation into the master project database.

Critical rules implemented here:
* every fact carries its source (document, page, paragraph, snippet);
* differing values for the same field across documents are NEVER auto-resolved – the field
  becomes status "conflict" with all candidates listed for user verification;
* a user-confirmed value is never overwritten; a disagreeing document flags a conflict;
* units and members are kept distinct (member register -> Unit rows with holder lists).
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from . import schema
from .textutil import legal_date, parse_date, to_float

MONTHS = r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
DATE = rf"(\d{{1,2}}(?:st|nd|rd|th)?\s+(?:day\s+of\s+)?{MONTHS},?\s+\d{{4}}|\d{{1,2}}[./-]\d{{1,2}}[./-]\d{{4}}|{MONTHS}\s+\d{{1,2}},?\s+\d{{4}})"
AMT = r"(?:Rs\.?|₹|INR)\s*([\d,]+(?:\.\d+)?)\s*(?:/-)?\s*(lakhs?|lacs?|crores?)?"
NODES = ["CBD Belapur", "Belapur", "Vashi", "Nerul", "Sanpada", "Koparkhairane", "Kopar Khairane", "Ghansoli", "Airoli", "Kharghar",
         "Kamothe", "Kalamboli", "New Panvel", "Panvel", "Ulwe", "Dronagiri", "Juinagar", "Seawoods", "Turbhe", "Taloja", "Rabale", "Mahape"]


@dataclass
class Rule:
    field: str
    pattern: str
    doc_types: tuple | None = None     # restrict to these doc types (None = any)
    group: int = 1
    kind: str = "text"                 # text | date | number | money | int
    category: str = "legal"
    flags: int = re.I


RULES: list[Rule] = [
    Rule("society.name", r"(?<![A-Za-z])((?:[A-Z][A-Za-z.\-']*\s+){1,6}?(?i:Co-?\s*op(?:erative|\.)?\s*(?:Hsg\.?|Housing)\.?\s*Soc(?:iety|\.)?\s*(?:Ltd\.?|Limited)))", None, flags=0),
    Rule("society.reg_no", r"Reg(?:istration|n)?\.?\s*No\.?\s*[:.\-]?\s*([A-Z]{2,6}\s*[/(][A-Za-z0-9()\s/.\-]{3,40}?\d{4}(?:\s*-\s*\d{2,4})?)", ("society_registration", "bye_laws", "sgbm_minutes", "order_79a", "lease_deed"), flags=0),
    Rule("society.reg_date", rf"(?:registered|registration)[^.]{{0,80}}?(?:on|dated)\s+{DATE}", ("society_registration",), kind="date"),
    Rule("society.pan", r"PAN(?:\s*No\.?)?\s*[:\-]?\s*([A-Z]{5}\d{4}[A-Z])", ("society_registration", "bye_laws", "sgbm_minutes"), flags=0),
    Rule("society.chairman", r"Chairman\s*[:\-–]\s*((?:Shri|Smt|Mr|Mrs|Ms|Dr)\.?\s+[A-Z][A-Za-z.\s]{3,40}?)(?=\s*(?:\n|,|;|Secretary|Treasurer|$))", None),
    Rule("society.secretary", r"Secretary\s*[:\-–]\s*((?:Shri|Smt|Mr|Mrs|Ms|Dr)\.?\s+[A-Z][A-Za-z.\s]{3,40}?)(?=\s*(?:\n|,|;|Chairman|Treasurer|$))", None),
    Rule("society.treasurer", r"Treasurer\s*[:\-–]\s*((?:Shri|Smt|Mr|Mrs|Ms|Dr)\.?\s+[A-Z][A-Za-z.\s]{3,40}?)(?=\s*(?:\n|,|;|Chairman|Secretary|$))", None),
    Rule("society.sgbm_redevelopment_date", rf"(?:resolved|decided)[^.]{{0,80}}redevelop[^.]{{0,200}}?(?:meeting|SGBM|SGM)[^.]{{0,30}}?(?:held\s+)?on\s+{DATE}", ("sgbm_minutes",), kind="date"),
    Rule("society.sgbm_redevelopment_date", rf"(?:SGBM|SGM|special general body meeting)\s+(?:held\s+)?on\s+{DATE}[^.]{{0,120}}redevelop(?:ment)?\s+of", ("sgbm_minutes",), kind="date"),
    Rule("society.sgbm_selection_date", rf"(?:SGBM|SGM|special general body meeting)\s+(?:held\s+)?on\s+{DATE}[^.]{{0,200}}(?:select|appoint)[^.]{{0,40}}developer", ("sgbm_minutes", "order_79a"), kind="date"),
    Rule("society.sgbm_selection_present", r"(\d+)\s+members?\s+(?:were\s+)?present", ("sgbm_minutes", "order_79a"), kind="int"),
    Rule("society.order_79a_date", rf"(?:order|NOC)[^.]{{0,60}}?dated\s+{DATE}", ("order_79a",), kind="date"),
    Rule("society.appointment_letter_date", rf"(?:letter of appointment|appointment letter)[^.]{{0,40}}?dated\s+{DATE}", None, kind="date"),
    Rule("society.tender_notice_date", rf"tender\s+notice[^.]{{0,40}}?dated\s+{DATE}", None, kind="date"),
    Rule("society.bidders_count", r"(\d+)\s*\(?[A-Za-z\- ]*\)?\s*(?:developers|bidders|offers)\s+(?:had\s+)?(?:submitted|participated|were received)", ("evaluation_report", "sgbm_minutes", "tender"), kind="int"),
    Rule("pmc.name", r"(M/s\.?\s*[A-Z][A-Za-z&.\s]{3,80}?)\s*(?:,|\()?\s*(?:as\s+(?:its\s+)?)?(?:the\s+)?(?:Project Management Consultant|PMC)", None),
    Rule("property.plot_no", r"Plot\s*No\.?\s*[:\-]?\s*([0-9A-Z][\w/\-]{0,12})", ("lease_deed", "agreement_to_lease", "cidco_noc", "feasibility", "area_statement", "society_registration", "property_tax")),
    Rule("property.sector", r"Sector[\s\-–:]*(?:No\.?\s*)?(\d{1,3}[A-Z]?)\b", ("lease_deed", "agreement_to_lease", "cidco_noc", "feasibility", "area_statement", "property_tax")),
    Rule("property.node", r"\b(" + "|".join(NODES) + r")\b", ("lease_deed", "agreement_to_lease", "cidco_noc", "feasibility", "area_statement", "society_registration")),
    Rule("property.plot_area_sqm", r"(?:admeasuring|plot area|area of (?:the )?plot)[^\d]{0,30}([\d,]+(?:\.\d+)?)\s*(?:sq\.?\s*(?:mtrs?|metres?|meters?|m)\b|square\s+met(?:re|er)s?|sqm)", ("lease_deed", "agreement_to_lease", "feasibility", "area_statement", "cidco_noc", "property_tax"), kind="number", category="technical"),
    Rule("property.lease_deed_date", rf"(?:this\s+)?(?:deed of lease|lease deed)[^.]{{0,80}}?(?:made|executed|dated)[^.]{{0,20}}?(?:on|at\s+\w+\s+on)?\s*(?:this\s+)?{DATE}", ("lease_deed",), kind="date"),
    Rule("property.lease_reg_no", r"(?:Serial|Sr\.?|Document|Registration)\s*No\.?\s*[:\-]?\s*([A-Z]{2,5}\d{0,2}\s*-\s*\d{2,6}\s*-\s*\d{4})", ("lease_deed",), flags=0),
    Rule("property.lease_term_years", r"(?:period|term)\s+of\s+(\d{2,3})\s*(?:\([A-Za-z\- ]+\))?\s*years", ("lease_deed", "agreement_to_lease"), kind="int"),
    Rule("property.lease_commencement", rf"(?:commencing|with effect)\s+from\s+{DATE}", ("lease_deed",), kind="date"),
    *[Rule(f"property.boundary_{d.lower()}", r"(?:towards\s+the\s+)?" + d + r"\s*[:\-–]+\s*([^:;\n]{3,60}?)\s*(?=[;,]|\.?\s*(?:On\s+)?(?:or\s+)?(?:towards\s+)?(?:the\s+)?(?:North|South|East|West)\b|\.?$)",
           ("lease_deed", "agreement_to_lease", "plans", "area_statement")) for d in ("North", "South", "East", "West")],
    Rule("property.units_count", r"(\d{1,4})\s*(?:\([A-Za-z\- ]+\)\s*)?(?:residential\s+)?(?:flats|tenements|units|apartments)\b", ("lease_deed", "society_registration", "structural_audit", "feasibility", "area_statement"), kind="int", category="member"),
    Rule("property.construction_year", r"(?:constructed|built)\s+(?:in|around|in or around)\s+(?:the\s+year\s+)?(19\d{2}|20\d{2})", None, kind="int"),
    Rule("property.structural_audit", r"((?:category|classified as)\s+C[- ]?\d[AB]?[^.]{0,80})", ("structural_audit",), category="technical"),
    Rule("developer.name", r"((?:M/s\.?\s*)?[A-Z][A-Za-z&.\s]{2,60}?(?:Pvt\.?\s*Ltd\.?|Private\s+Limited|LLP|Infra(?:con|structure)?\s+(?:Pvt\.?\s*)?Ltd\.?|Developers|Builders|Realty|Superstructures?\s+Pvt\.?\s*Ltd\.?))", ("final_offer", "developer_incorporation", "developer_board_resolution", "developer_financials", "appointment_letter"), flags=0),
    Rule("developer.cin", r"\b([LU]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6})\b", ("final_offer", "developer_incorporation", "developer_board_resolution", "developer_financials"), flags=0),
    Rule("developer.pan", r"PAN(?:\s*No\.?)?\s*[:\-]?\s*([A-Z]{5}\d{4}[A-Z])", ("final_offer", "developer_incorporation", "developer_board_resolution", "developer_financials"), flags=0),
    Rule("developer.gstin", r"GST(?:IN)?(?:\s*No\.?)?\s*[:\-]?\s*(\d{2}[A-Z]{5}\d{4}[A-Z]\d[A-Z][A-Z\d])", ("final_offer", "developer_incorporation", "developer_financials"), flags=0),
    Rule("developer.offer_date", rf"(?:final|no regret)?\s*offer[^.]{{0,30}}?dated\s+{DATE}", ("final_offer", "appointment_letter", "sgbm_minutes"), kind="date"),
    Rule("developer.offer_date", rf"^\s*Date\s*[:\-]\s*{DATE}", ("final_offer",), kind="date", flags=re.I | re.M),
    Rule("developer.net_worth", rf"net[- ]?worth[^.]{{0,60}}?{AMT}", ("developer_financials", "final_offer", "evaluation_report"), group=0, kind="money", category="commercial"),
    Rule("developer.board_resolution_date", rf"(?:meeting of the board|board meeting|board of directors)[^.]{{0,60}}?(?:held\s+)?on\s+{DATE}", ("developer_board_resolution",), kind="date"),
    # commercial terms (only from offer / evaluation / minutes)
    Rule("comm.rent_monthly", rf"(?:monthly\s+)?(?:rent|displacement compensation)[^.%]{{0,80}}?{AMT}\s*(?:per\s+month|p\.?m\.?|/\s*month)?\s*(?:per\s+(?:flat|unit|member|tenement))", ("final_offer", "evaluation_report", "sgbm_minutes"), group=0, kind="money", category="commercial"),
    Rule("comm.rent_per_sqft", rf"rent[^.]{{0,60}}?{AMT}\s*per\s*sq\.?\s*ft", ("final_offer", "evaluation_report"), group=0, kind="money", category="commercial"),
    Rule("comm.rent_escalation_percent", r"(?:escalat\w*|increase\w*)[^.%]{0,60}?(\d{1,2}(?:\.\d+)?)\s*%", ("final_offer", "evaluation_report", "sgbm_minutes"), kind="number", category="commercial"),
    Rule("comm.rent_escalation_months", r"(?:escalat\w*|increase\w*)[^.]{0,80}?(?:every|after every|each)\s+(\d{1,2})\s*(?:\([A-Za-z\- ]+\))?\s*months", ("final_offer", "evaluation_report"), kind="int", category="commercial"),
    Rule("comm.brokerage", rf"brokerage[^.%]{{0,60}}?{AMT}", ("final_offer", "evaluation_report", "sgbm_minutes"), group=0, kind="money", category="commercial"),
    Rule("comm.deposit", rf"(?:refundable\s+)?(?:security\s+)?deposit[^.%]{{0,60}}?{AMT}", ("final_offer", "evaluation_report"), group=0, kind="money", category="commercial"),
    Rule("comm.shifting", rf"(?<!re-)(?<!re)shifting[^.%]{{0,60}}?{AMT}", ("final_offer", "evaluation_report", "sgbm_minutes"), group=0, kind="money", category="commercial"),
    Rule("comm.reshifting", rf"re-?\s*shifting[^.%]{{0,60}}?{AMT}", ("final_offer", "evaluation_report"), group=0, kind="money", category="commercial"),
    Rule("comm.corpus", rf"corpus(?:\s+fund)?[^.%]{{0,60}}?{AMT}", ("final_offer", "evaluation_report", "sgbm_minutes"), group=0, kind="money", category="commercial"),
    Rule("comm.hardship", rf"hardship[^.%]{{0,60}}?{AMT}", ("final_offer", "evaluation_report"), group=0, kind="money", category="commercial"),
    Rule("comm.society_office_rent", rf"society\s+office[^.%]{{0,60}}?rent[^.%]{{0,30}}?{AMT}", ("final_offer",), group=0, kind="money", category="commercial"),
    Rule("security.bg_amount", rf"bank\s+guarantee[^.%]{{0,80}}?{AMT}", ("final_offer", "evaluation_report", "sgbm_minutes"), group=0, kind="money", category="commercial"),
    Rule("security.ld_per_month", rf"(?:liquidated damages|penalty)[^.%]{{0,80}}?{AMT}\s*(?:per\s+month)", ("final_offer", "evaluation_report"), group=0, kind="money", category="commercial"),
    Rule("time.construction_months", r"(?:complet\w+|construction period)[^.]{0,80}?(\d{2})\s*(?:\([A-Za-z\- ]+\))?\s*months", ("final_offer", "evaluation_report", "feasibility"), kind="int"),
    Rule("time.grace_months", r"grace\s+period\s+of\s+(\d{1,2})\s*(?:\([A-Za-z\- ]+\))?\s*months", ("final_offer", "evaluation_report"), kind="int"),
    Rule("time.approval_months", r"(?:approvals?|commencement certificate)[^.]{0,60}?within\s+(\d{1,2})\s*(?:\([A-Za-z\- ]+\))?\s*months", ("final_offer", "evaluation_report"), kind="int"),
    Rule("tech.additional_area_percent", r"(\d{1,3}(?:\.\d+)?)\s*%\s*(?:additional|extra|more)\s*(?:RERA\s+)?(?:carpet\s+)?area", ("final_offer", "evaluation_report", "feasibility"), kind="number", category="technical"),
    Rule("tech.parking_per_unit", r"(\d)\s*\(?[A-Za-z]*\)?\s*(?:car\s+)?parking\s+(?:space\s+)?(?:per|for each)\s+(?:flat|unit|member)", ("final_offer", "evaluation_report", "feasibility"), kind="int", category="technical"),
    Rule("tech.total_potential_sqm", r"(?:total|full)\s+(?:development\s+)?potential[^.\d]{0,40}([\d,]+(?:\.\d+)?)\s*(?:sq\.?\s*m|square\s+met)", ("feasibility", "area_statement"), kind="number", category="technical"),
    Rule("tech.excess_area_rate", rf"additional\s+area[^.]{{0,80}}?{AMT}\s*per\s*sq", ("final_offer",), group=0, kind="money", category="commercial"),
]


def _norm_amount(m: re.Match) -> str | None:
    s = m.group(0)
    mm = re.search(AMT, s, re.I)
    if not mm:
        return None
    n = to_float(mm.group(1))
    if n is None:
        return None
    unit = (mm.group(2) or "").lower()
    if unit.startswith("lakh") or unit.startswith("lac"):
        n *= 100_000
    elif unit.startswith("crore"):
        n *= 10_000_000
    return str(int(round(n)))


def normalize(kind: str, raw: str) -> str:
    if kind == "date":
        d = parse_date(raw)
        return d.isoformat() if d else raw.strip().lower()
    if kind in ("number", "int", "money"):
        f = to_float(raw)
        return ("%g" % f) if f is not None else raw
    return re.sub(r"[^a-z0-9]", "", raw.lower())


def run_rules(segments: list[dict], doc_type: str) -> list[dict]:
    facts = []
    for seg in segments:
        text = seg["text"]
        for r in RULES:
            if r.doc_types and doc_type not in r.doc_types:
                continue
            for m in re.finditer(r.pattern, text, r.flags):
                if r.kind == "money":
                    val = _norm_amount(m)
                    if not val:
                        continue
                else:
                    val = (m.group(r.group) or "").strip(" ,;:.")
                if not val:
                    continue
                if r.kind == "date":
                    d = parse_date(val)
                    if not d:
                        continue
                    val = d.isoformat()
                facts.append({"field": r.field, "value": val, "normalized": normalize(r.kind, val),
                              "page": seg.get("page"), "paragraph": seg.get("para"),
                              "snippet": text[max(0, m.start() - 60): m.end() + 60],
                              "method": "ocr-rule" if seg.get("ocr") else "rule",
                              "confidence": 0.55 if seg.get("ocr") else 0.75, "category": r.category})
                break  # first match per rule per segment
    # keep one fact per (field, normalized value) per document (earliest occurrence)
    seen, out = set(), []
    for f in facts:
        k = (f["field"], f["normalized"])
        if k not in seen:
            seen.add(k); out.append(f)
    # boundaries: take only the first hit per direction per document
    first = {}
    final = []
    for f in out:
        if f["field"].startswith("property.boundary") or f["field"] in ("society.name", "developer.name", "property.node", "property.plot_no", "property.sector"):
            if f["field"] in first:
                continue
            first[f["field"]] = True
        final.append(f)
    return final


# ------------------------------------------------------------------ member register
HEAD = {
    "unit_no": ["flat no", "unit no", "room no", "flat", "unit", "room", "shop no", "premises"],
    "name": ["name of member", "member name", "name of the member", "members", "member", "name", "owner"],
    "building": ["building", "bldg", "wing"],
    "floor": ["floor"],
    "unit_type": ["type"],
    "existing_rera_carpet_sqft": ["existing rera carpet", "rera carpet", "existing carpet", "carpet area", "carpet"],
    "existing_mofa_carpet_sqft": ["mofa"],
    "existing_builtup_sqft": ["built up", "built-up", "bua"],
    "new_rera_carpet_sqft": ["new rera", "new carpet", "proposed carpet", "new area", "entitlement", "proposed area", "new flat area"],
    "balcony_sqft": ["balcony", "terrace"],
    "share_cert_no": ["share cert", "share certificate", "certificate no"],
    "mortgage": ["bank", "mortgage", "loan", "lender"],
    "status": ["status", "remark", "remarks"],
    "consent": ["consent"],
    "society_dues": ["dues", "outstanding"],
    "parking": ["parking"],
    "use": ["use", "residential/commercial"],
}


def _map_header(header: list[str]) -> dict[str, int]:
    mapping: dict[str, int] = {}
    h = [re.sub(r"\s+", " ", (c or "").lower()) for c in header]
    for key, words in HEAD.items():
        for w in words:
            for i, c in enumerate(h):
                if w in c and i not in mapping.values():
                    if key == "name" and ("bank" in c or "lender" in c):
                        continue
                    if key == "existing_rera_carpet_sqft" and ("new" in c or "proposed" in c or "mofa" in c):
                        continue
                    if key == "unit_type" and "flat type" not in c and c.strip() != "type" and "unit type" not in c:
                        continue
                    mapping[key] = i
                    break
            if key in mapping:
                break
    return mapping


def _is_sqm(header_cell: str) -> bool:
    return bool(re.search(r"sq\.?\s*m(?!i)|sqm|sq\.?\s*mtr|square met", (header_cell or "").lower()))


def parse_member_tables(tables: list[dict], doc_name: str, doc_id: int | None) -> list[dict]:
    units = []
    for tb in tables:
        rows = tb["rows"]
        # find header row within first 5 rows
        hi, mapping = None, {}
        for i, r in enumerate(rows[:5]):
            m = _map_header(r)
            if "unit_no" in m and "name" in m:
                hi, mapping = i, m
                break
        if hi is None:
            continue
        header = rows[hi]
        for ri, r in enumerate(rows[hi + 1:], hi + 2):
            def g(k):
                i = mapping.get(k)
                return (r[i] if i is not None and i < len(r) else "") or ""
            unit_no = g("unit_no").strip()
            if not unit_no or unit_no.lower() in ("total", "grand total"):
                continue
            names_raw = g("name").strip()
            holders = []
            for part in re.split(r"\s*(?:&|/|\band\b|;)\s*", names_raw):
                part = part.strip(" ,")
                if not part:
                    continue
                share = None
                sm = re.search(r"\((\d{1,3}\s*%)\)", part)
                if sm:
                    share = sm.group(1); part = part.replace(sm.group(0), "").strip()
                st = "deceased" if re.match(r"late\b", part, re.I) else "alive"
                part = re.sub(r"^late\.?\s+", "", part, flags=re.I)
                holders.append({"name": part, "share": share, "status": st})
            u = {"unit_no": unit_no, "holders": holders, "building": g("building"), "floor": g("floor"), "unit_type": g("unit_type"),
                 "mortgage": g("mortgage"), "status": "regular", "share_cert_no": g("share_cert_no"), "parking": g("parking"),
                 "consent": (g("consent") or "unknown").lower()[:20],
                 "sources": [{"doc_id": doc_id, "doc": doc_name, "page": tb.get("page"), "para": ri, "snippet": " | ".join(map(str, r))[:200]}]}
            stat = g("status").lower()
            if "deceas" in stat or "expired" in stat or any(h["status"] == "deceased" for h in holders):
                u["status"] = "deceased-heirship"
                if holders and not any(h["status"] == "deceased" for h in holders):
                    holders[0]["status"] = "deceased"
            elif "transfer" in stat:
                u["status"] = "transfer-pending"
            elif "dispute" in stat or "litigation" in stat:
                u["status"] = "dispute"
            if stat:
                u["notes"] = g("status")
            for k in ("existing_rera_carpet_sqft", "existing_mofa_carpet_sqft", "existing_builtup_sqft", "new_rera_carpet_sqft", "balcony_sqft"):
                v = to_float(re.sub(r"[^\d.]", "", g(k)) or None) if g(k) else None
                if v is not None and _is_sqm(header[mapping[k]]):
                    v = round(v * 10.764, 2)
                u[k] = v
            u["society_dues"] = to_float(re.sub(r"[^\d.]", "", g("society_dues")) or None) if g("society_dues") else None
            if g("use"):
                u["use"] = "Commercial" if re.search(r"shop|comm", g("use"), re.I) else "Residential"
            elif re.search(r"shop", unit_no, re.I):
                u["use"] = "Commercial"
            units.append(u)
    return units


# ------------------------------------------------------------------ consolidation
def consolidate(data: dict, facts: list[dict], docs_by_id: dict[int, dict]) -> dict:
    """Merge extracted facts into the master database. Returns the updated data dict."""
    by_field: dict[str, list[dict]] = {}
    for f in facts:
        by_field.setdefault(f["field"], []).append(f)
    for key, fs in by_field.items():
        fdef = schema.FIELD_MAP.get(key)
        if not fdef:
            continue
        entry = dict(data.get(key) or schema.empty_entry(fdef))
        groups: dict[str, dict] = {}
        for f in fs:
            src = {"doc_id": f["document_id"], "doc": docs_by_id.get(f["document_id"], {}).get("filename", "?"),
                   "page": f.get("page"), "para": f.get("paragraph"), "snippet": f.get("snippet", "")[:220], "method": f.get("method")}
            g = groups.setdefault(f["normalized"], {"value": f["value"], "sources": []})
            g["sources"].append(src)
        cands = list(groups.values())
        for cnd in cands:
            if fdef.type == "date":
                cnd["display"] = legal_date(cnd["value"])
        if entry.get("status") == "confirmed" and not entry.get("note", "").startswith("Drafting default"):
            confirmed_norm = normalize(_kind(fdef), str(entry.get("value")))
            disagree = [c for c in cands if normalize(_kind(fdef), str(c["value"])) != confirmed_norm]
            if disagree:
                entry["status"] = "conflict"
                entry["candidates"] = [{"value": entry.get("value"), "sources": entry.get("sources", []), "label": "previously confirmed"}] + cands
                entry["note"] = "A newly uploaded document disagrees with the confirmed value – verify."
            data[key] = entry
            continue
        if len(cands) == 1:
            c = cands[0]
            ocr_only = all((s.get("method") or "").startswith("ocr") for s in c["sources"])
            entry.update({"value": _cast(fdef, c["value"]), "status": "verify" if ocr_only else "extracted",
                          "sources": c["sources"], "candidates": [],
                          "note": "Read by OCR – verify against the original." if ocr_only else f"Found in {len(c['sources'])} place(s)."})
        else:
            entry.update({"value": None, "status": "conflict", "candidates": cands, "sources": [s for c in cands for s in c["sources"]],
                          "note": f"{len(cands)} different values found in uploaded documents – not auto-selected. Verify and confirm one."})
        data[key] = entry
    return data


def _kind(f: schema.F) -> str:
    return {"date": "date", "int": "int", "number": "number", "money": "money", "area_sqm": "number", "area_sqft": "number",
            "percent": "number", "months": "int", "years": "int"}.get(f.type, "text")


def _cast(f: schema.F, v):
    if f.type in ("int", "months", "years"):
        x = to_float(v)
        return int(x) if x is not None else v
    if f.type in ("money", "number", "percent", "area_sqm", "area_sqft"):
        x = to_float(v)
        return (int(x) if x is not None and x.is_integer() else x) if x is not None else v
    return v
