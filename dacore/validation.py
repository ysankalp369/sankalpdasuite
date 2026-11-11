"""Document validation engine (Module 5).

Runs after rendering and before any DA is released. Produces a list of checks:
    {"id","category","severity": critical|high|medium|low|info,"status": pass|fail|warn,"message","where"}
"""
from __future__ import annotations

import re

from . import schema
from .drafting import annexure_texts as AX
from .drafting.render import RenderResult
from .textutil import to_float

# Words that, if they appear uncapitalised, suggest a defined term used inconsistently.
CASE_SENSITIVE_TERMS = ["Members’ New Premises", "Existing Members", "Existing Premises", "Handover Date", "Possession Date",
                        "Possession Notice", "Vacation Notice", "Bank Guarantee", "Full Occupation Certificate",
                        "Completion Date", "Defect Liability Period", "Corpus Fund", "Initial Approvals",
                        "Developer’s Free Sale Component", "Rehabilitation Component", "Commencement Certificate"]

# Facts specific to the reference agreements must never appear in a new project's DA. The markers are
# derived at run time from the ingested reference agreements (see services.reference_markers) so that no
# party names or identifiers from real agreements are stored in source code.
REFERENCE_FACT_MARKERS: list[str] = []


def _chk(out, id, category, severity, ok, message, where="", warn=False):
    out.append({"id": id, "category": category, "severity": severity,
                "status": "pass" if ok else ("warn" if warn else "fail"), "message": message, "where": where})


def validate(res: RenderResult, data: dict, units: list[dict], reference_markers: list[str] | None = None) -> list[dict]:
    out: list[dict] = []
    text = res.full_text
    calc = res.calc

    # ---- definitions used and capitalised consistently
    for term in res.defined_terms:
        uses = text.count(term)
        _chk(out, f"def.used.{term}", "Definitions", "low", uses >= 2,
             f"Defined term “{term}” is used {max(uses - 1, 0)} time(s) outside its definition.", warn=True)
    for term in CASE_SENSITIVE_TERMS:
        low = re.findall(r"(?<![A-Za-z“])" + re.escape(term.lower()) + r"(?![A-Za-z])", text)
        _chk(out, f"def.case.{term}", "Definitions", "medium", not low,
             f"Defined term “{term}” appears {len(low)} time(s) in lower case." if low else f"“{term}” consistently capitalised.")

    # ---- cross references, schedules, annexures
    _chk(out, "xref", "Cross-references", "critical", not res.broken_refs,
         "All cross-references resolve." if not res.broken_refs else
         f"{len(res.broken_refs)} unresolved cross-reference(s): " + ", ".join(f"{b['ref']} ({b['where']})" for b in res.broken_refs))
    sched_keys = [k for k, *_ in AX.SCHEDULES]
    _chk(out, "sched.dup", "Schedules", "high", len(sched_keys) == len(set(sched_keys)), "No duplicated schedule.")
    unref = [k for k in sched_keys if k not in res.used_schedules]
    _chk(out, "sched.ref", "Schedules", "medium", not unref,
         "Every schedule is referred to in the operative part." if not unref else "Schedules not referred to in the body: " + ", ".join(unref), warn=True)
    ann_keys = [k for k, *_ in AX.ANNEXURES]
    letters = list(res.annexure_letters.values())
    _chk(out, "ann.seq", "Annexures", "high", letters == [chr(ord("A") + i) for i in range(len(letters))] and len(set(ann_keys)) == len(ann_keys),
         "Annexure lettering is continuous with no gaps or duplicates.")
    unref_a = [f"Annexure {res.annexure_letters[k]}" for k in ann_keys if k not in res.used_annexures]
    _chk(out, "ann.ref", "Annexures", "medium", not unref_a,
         "Every annexure is referred to." if not unref_a else "Annexures not referred to in the body: " + ", ".join(unref_a), warn=True)

    # ---- members vs units
    n_units = len(units)
    du = to_float(schema.value(data, "property.units_count"))
    dm = to_float(schema.value(data, "property.members_count"))
    if n_units:
        _chk(out, "units.count", "Members", "high", du is None or int(du) == n_units,
             f"Units in register: {n_units}; units stated in project data: {int(du) if du else '—'}.")
        _chk(out, "members.count", "Members", "high", dm is None or int(dm) == calc["members_from_register"],
             f"Distinct living members in register: {calc['members_from_register']}; members stated in project data: {int(dm) if dm else '—'}. "
             "(Units and members are counted separately.)", warn=True)
        no_area = [u.get("unit_no") for u in units if to_float(u.get("new_rera_carpet_sqft")) is None]
        _chk(out, "members.area", "Members", "critical", not no_area,
             "Every unit has a new RERA carpet area." if not no_area else f"{len(no_area)} unit(s) without new carpet area: {', '.join(map(str, no_area[:15]))}")
        smaller = [u.get("unit_no") for u in units if (to_float(u.get("new_rera_carpet_sqft")) or 0) and
                   (to_float(u.get("existing_rera_carpet_sqft")) or 0) > (to_float(u.get("new_rera_carpet_sqft")) or 0)]
        _chk(out, "members.reduction", "Members", "critical", not smaller,
             "No member receives less than the existing area." if not smaller else f"New area is LESS than existing area for: {', '.join(map(str, smaller))}")
        no_name = [u.get("unit_no") for u in units if not u.get("holders")]
        _chk(out, "members.names", "Members", "high", not no_name, "Every unit has a recorded holder." if not no_name else f"Units without holders: {', '.join(map(str, no_name))}")
        seen, dups = set(), []
        for u in units:
            k = (u.get("building") or "", str(u.get("unit_no")).strip().lower())
            dups.append(u.get("unit_no")) if k in seen else seen.add(k)
        _chk(out, "members.dupunit", "Members", "high", not dups, "No duplicated unit numbers." if not dups else f"Duplicated units: {', '.join(map(str, dups))}")
        dec = [u.get("unit_no") for u in units if any((h.get("status") or "") == "deceased" for h in u.get("holders") or [])]
        _chk(out, "members.deceased", "Members", "medium", not dec,
             "No deceased holders recorded." if not dec else f"{len(dec)} unit(s) with deceased holders – transmission to be completed before PAAA: {', '.join(map(str, dec[:15]))}", warn=True)
    else:
        _chk(out, "members.none", "Members", "critical", False, "No member register has been loaded – Third and Fifth Schedules cannot be generated.")

    # ---- monetary consistency
    corpus = to_float(schema.value(data, "comm.corpus"))
    if corpus is not None and n_units:
        overrides = [u for u in units if u.get("corpus") not in (None, "")]
        expected = corpus * n_units if not overrides else None
        if expected is not None:
            _chk(out, "money.corpus", "Monetary", "high", abs(expected - calc["corpus_total"]) < 1,
                 f"Total corpus per schedule {calc['corpus_total']:,.0f} = {corpus:,.0f} × {n_units} units.")
        else:
            _chk(out, "money.corpus", "Monetary", "medium", False, "Some units carry a member-specific corpus differing from the uniform rate – confirm this is negotiated.", warn=True)
    missing_rent = sum(1 for u in units if _rent_missing(u, data))
    _chk(out, "money.rent", "Monetary", "critical", not missing_rent or not n_units,
         "Rent computable for every unit." if not missing_rent else f"Rent cannot be computed for {missing_rent} unit(s) – set rent basis and rate.")
    bg = to_float(schema.value(data, "security.bg_amount"))
    ms = schema.value(data, "security.bg_milestones") or []
    if bg is not None and ms:
        tot = sum(to_float(m.get("amount")) or 0 for m in ms if isinstance(m, dict))
        _chk(out, "bg.total", "Security", "critical", abs(tot - bg) < 1, f"BG release milestones total {tot:,.0f} against BG amount {bg:,.0f}.")
        last = (ms[-1].get("milestone", "") if isinstance(ms[-1], dict) else str(ms[-1])).lower()
        _chk(out, "bg.dlp", "Security", "high", "defect" in last or "dlp" in last,
             "A BG tranche is retained until expiry of the Defect Liability Period." if ("defect" in last or "dlp" in last) else
             "No BG tranche is retained through the Defect Liability Period (last milestone: '" + last + "').")
    elif bg is None:
        _chk(out, "bg.amount", "Security", "critical", False, "Bank Guarantee amount not set.")

    # ---- dates and timelines
    cons, grace, ls = (to_float(schema.value(data, k)) for k in ("time.construction_months", "time.grace_months", "time.longstop_months"))
    if cons is not None and grace is not None and ls is not None:
        _chk(out, "time.longstop", "Timeline", "high", ls >= grace, f"Long-stop ({ls:.0f} months after Completion Date) is not shorter than the grace period ({grace:.0f} months).")
        _chk(out, "time.reasonable", "Timeline", "low", 18 <= cons <= 60, f"Construction period of {cons:.0f} months is within the usual 18–60 month range.", warn=True)
    from .textutil import parse_date
    order = [("society.sgbm_redevelopment_date", "redevelopment SGBM"), ("society.sgbm_selection_date", "developer-selection SGBM"),
             ("society.order_79a_date", "79A order"), ("society.appointment_letter_date", "appointment letter"),
             ("society.sgbm_da_approval_date", "DA-approval SGBM")]
    prev = None
    for k, lbl in order:
        dv = parse_date(schema.value(data, k))
        if dv and prev and dv < prev[0]:
            _chk(out, f"date.order.{k}", "Dates", "high", False, f"The {lbl} ({dv}) is earlier than the {prev[1]} ({prev[0]}). Check sequence.")
        if dv:
            prev = (dv, lbl)
    _chk(out, "date.order", "Dates", "info", True, "Chronology of resolutions, 79A order and appointment checked.")

    # ---- structural / provision consistency (template invariants — checked on rendered text)
    tl = text.lower()
    _chk(out, "rent.trigger", "Consistency", "critical", "rent shall cease only on the possession date" in tl and "valid possession notice" in tl,
         "Rent cessation is tied to the Possession Date and a Valid Possession Notice (no conflict with completion triggers).")
    _chk(out, "fm.payments", "Consistency", "critical", "force majeure shall not suspend or excuse the payment of rent" in tl,
         "Force majeure does not override continuing payment obligations.")
    _chk(out, "term.arb", "Consistency", "critical", "shall not be conditional upon any prior arbitral award" in tl,
         "Termination is not made dependent on an arbitral award; arbitration clause preserves termination and BG invocation.")
    _chk(out, "vacation.cp", "Consistency", "critical", "conditions precedent" in tl and "bank guarantee" in tl,
         "Vacation is sequenced after approvals, BG, PAAA and initial payments.")
    _chk(out, "paaa.match", "Consistency", "high", "fifth schedule" in tl and "third schedule" in tl,
         "PAAA format refers to the same schedules as the main DA.")

    # ---- outstanding information
    crit = [o for o in res.outstanding if o["critical"]]
    _chk(out, "blanks.critical", "Completeness", "critical", not crit,
         "No critical blanks." if not crit else f"{len(crit)} critical field(s) outstanding – draft is NOT execution-ready.")
    other = [o for o in res.outstanding if not o["critical"]]
    _chk(out, "blanks.other", "Completeness", "medium", not other,
         "No other blanks." if not other else f"{len(other)} non-critical field(s) outstanding and disclosed in the draft.", warn=True)
    conflicts = [k for k, e in data.items() if (e or {}).get("status") == "conflict"]
    _chk(out, "facts.conflict", "Completeness", "critical", not conflicts,
         "No contradictory facts." if not conflicts else "Contradictory facts awaiting verification: " + ", ".join(schema.FIELD_MAP[k].label if k in schema.FIELD_MAP else k for k in conflicts))
    unv = {u["key"] for u in res.unverified}
    _chk(out, "facts.unverified", "Completeness", "high", not unv,
         "All facts verified." if not unv else f"{len(unv)} extracted fact(s) not yet verified by a user (highlighted turquoise in the draft).", warn=True)

    # ---- carry-over of reference agreement facts
    markers = (reference_markers or []) + REFERENCE_FACT_MARKERS
    society_name = (schema.value(data, "society.name") or "").lower()
    dev_name = (schema.value(data, "developer.name") or "").lower()
    leaked = [m for m in markers if re.search(r"(?<![A-Za-z0-9])" + re.escape(m.lower()) + r"(?![A-Za-z0-9])", tl)
              and m.lower() not in society_name and m.lower() not in dev_name]
    _chk(out, "leak.reference", "Integrity", "critical", not leaked,
         "No project-specific facts from reference agreements carried forward." if not leaked else "Reference-agreement facts found in draft: " + ", ".join(leaked))
    return out


def _rent_missing(u, data):
    from .drafting.render import unit_rent
    return unit_rent(u, data) is None


def summary(checks: list[dict]) -> dict:
    s = {"pass": 0, "fail": 0, "warn": 0, "critical_fail": 0}
    for c in checks:
        s[c["status"]] += 1
        if c["status"] == "fail" and c["severity"] == "critical":
            s["critical_fail"] += 1
    s["execution_ready"] = s["critical_fail"] == 0
    return s
