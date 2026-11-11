"""Rendering engine: Master DA template + project database -> structured document model.

The model is a list of blocks consumed by docx_builder.py. Every placeholder that cannot be
filled is rendered as a highlighted "[● … OUTSTANDING]" marker and recorded, so that a draft
with unresolved critical blanks can never be mistaken for an execution-ready instrument.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .. import schema
from ..textutil import (indian_grouping, legal_date, money, money_short, norm_name, num_words,
                        to_float)
from . import annexure_texts as AX
from .master_da import ARTICLE_ANCHORS, ARTICLES, DEFINITIONS, PARTIES, RECITALS, C

PH = re.compile(r"\{\{(?:(money|num|date|upper|words):)?([\w.]+)\}\}")
REF = re.compile(r"\[\[(ref|art|sch|ann):([\w.]+)\]\]")
ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII", "XIII", "XIV", "XV",
         "XVI", "XVII", "XVIII", "XIX", "XX", "XXI", "XXII", "XXIII", "XXIV", "XXV"]
LETTERS = "abcdefghijklmnopqrstuvwxyz"
SMALL_ROMAN = ["i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x", "xi", "xii"]
SQM_TO_SQFT = 10.764


@dataclass
class RenderResult:
    blocks: list[dict] = field(default_factory=list)
    outstanding: list[dict] = field(default_factory=list)   # {"key","label","where","critical"}
    unverified: list[dict] = field(default_factory=list)
    broken_refs: list[dict] = field(default_factory=list)
    ref_map: dict[str, str] = field(default_factory=dict)
    used_schedules: set[str] = field(default_factory=set)
    used_annexures: set[str] = field(default_factory=set)
    schedule_names: dict[str, str] = field(default_factory=dict)
    annexure_letters: dict[str, str] = field(default_factory=dict)
    defined_terms: list[str] = field(default_factory=list)
    calc: dict[str, Any] = field(default_factory=dict)
    full_text: str = ""


# ------------------------------------------------------------------ computed values
def distinct_members(units: list[dict]) -> int:
    names = set()
    for u in units:
        for h in u.get("holders") or []:
            if (h.get("status") or "").lower() in ("deceased",):
                continue
            n = norm_name(h.get("name", ""))
            if n:
                names.add(n)
    return len(names)


def unit_rent(u: dict, data: dict) -> float | None:
    if u.get("monthly_rent") not in (None, ""):
        return to_float(u["monthly_rent"])
    basis = schema.value(data, "comm.rent_basis", "") or ""
    if basis.startswith("per sq"):
        rate = to_float(schema.value(data, "comm.rent_per_sqft"))
        area = to_float(u.get("existing_rera_carpet_sqft"))
        return round(rate * area) if rate is not None and area is not None else None
    return to_float(schema.value(data, "comm.rent_monthly"))


def unit_amount(u: dict, data: dict, unit_key: str, field_key: str) -> float | None:
    if u.get(unit_key) not in (None, ""):
        return to_float(u[unit_key])
    return to_float(schema.value(data, field_key))


def compute(data: dict, units: list[dict]) -> dict:
    calc: dict[str, Any] = {"units_from_register": len(units), "members_from_register": distinct_members(units)}
    calc["existing_sqft_total"] = round(sum(to_float(u.get("existing_rera_carpet_sqft")) or 0 for u in units), 2)
    calc["new_sqft_total"] = round(sum(to_float(u.get("new_rera_carpet_sqft")) or 0 for u in units), 2)
    rents = [unit_rent(u, data) for u in units]
    calc["rent_total_month"] = sum(r for r in rents if r is not None)
    for k, f in (("deposit", "comm.deposit"), ("brokerage", "comm.brokerage"), ("shifting", "comm.shifting"),
                 ("corpus", "comm.corpus"), ("hardship", "comm.hardship")):
        vals = [unit_amount(u, data, k, f) for u in units]
        calc[f"{k}_total"] = sum(v for v in vals if v is not None)
    resh = to_float(schema.value(data, "comm.reshifting"))
    calc["reshifting_total"] = (resh or 0) * len(units)
    return calc


# ------------------------------------------------------------------ renderer
class Renderer:
    def __init__(self, data: dict, units: list[dict], project_docs: list[dict] | None = None):
        self.data = dict(data)
        self.units = units
        self.docs = project_docs or []
        self.res = RenderResult()
        self.calc = compute(self.data, units)
        self.res.calc = self.calc
        self._fill_computed()
        self.where = ""
        self.schedules = [s for s in AX.SCHEDULES]
        self.res.schedule_names = {k: f"the {t.title()}" for k, t, _ in self.schedules}
        self.res.annexure_letters = {k: chr(ord("A") + i) for i, (k, *_r) in enumerate(AX.ANNEXURES)}

    # computed fallbacks (never override a value set from documents / users)
    def _fill_computed(self):
        def fallback(key, val, note):
            e = self.data.get(key) or {}
            if e.get("status") in (None, "missing") and val not in (None, 0, ""):
                self.data[key] = {"value": val, "status": "extracted", "sources": [{"doc": "Member register (computed)"}], "note": note}
        fallback("property.units_count", self.calc["units_from_register"] or None, "Counted from member register")
        fallback("property.members_count", self.calc["members_from_register"] or None, "Distinct living holders in member register")
        if self.calc["new_sqft_total"]:
            fallback("tech.rehab_carpet_total_sqft", indian_grouping(self.calc["new_sqft_total"]), "Sum of unit-wise new carpet areas")
        if self.calc["existing_sqft_total"]:
            fallback("property.existing_carpet_total_sqm", f"{self.calc['existing_sqft_total'] / SQM_TO_SQFT:,.2f}", "Sum of unit-wise existing carpet areas")

    # -------------------------------------------------- value resolution
    def _cond(self, when: str | None) -> bool:
        if not when:
            return True
        v = schema.value(self.data, when)
        return v not in (None, "", [], 0, "0")

    def _fmt(self, fmt: str | None, key: str):
        f = schema.FIELD_MAP.get(key)
        e = self.data.get(key) or {}
        v = schema.value(self.data, key)
        if v is None:
            label = f.label if f else key
            self.res.outstanding.append({"key": key, "label": label, "where": self.where,
                                         "critical": bool(f and f.critical), "status": e.get("status", "missing")})
            tag = "CONFLICT – VERIFY" if e.get("status") == "conflict" else "OUTSTANDING"
            return f"[● {label} – {tag}]", "missing"
        if isinstance(v, list):
            v = "; ".join(str(x.get("milestone", x)) if isinstance(x, dict) else str(x) for x in v)
        if fmt == "money":
            s = money(v)
        elif fmt == "num":
            s = num_words(v)
        elif fmt == "date":
            s = legal_date(v)
        elif fmt == "upper":
            s = str(v).upper()
        else:
            s = str(v)
        kind = "fill"
        if e.get("status") in ("extracted", "verify"):
            kind = "unverified"
            self.res.unverified.append({"key": key, "label": f.label if f else key, "value": s, "where": self.where})
        return s, kind

    def _ref(self, kind: str, key: str) -> str:
        if kind == "ref":
            num = self.res.ref_map.get(key)
            if not num:
                self.res.broken_refs.append({"ref": key, "where": self.where})
                return f"[● cross-reference ‘{key}’ unresolved]"
            return f"Clause {num}"
        if kind == "art":
            roman = ARTICLE_ANCHORS.get(key)
            if not roman:
                self.res.broken_refs.append({"ref": "art:" + key, "where": self.where})
                return f"[● Article ‘{key}’ unresolved]"
            return f"Article {roman}"
        if kind == "sch":
            name = self.res.schedule_names.get(key)
            if not name:
                self.res.broken_refs.append({"ref": "sch:" + key, "where": self.where})
                return f"[● schedule ‘{key}’ unresolved]"
            self.res.used_schedules.add(key)
            return name
        if kind == "ann":
            letter = self.res.annexure_letters.get(key)
            if not letter:
                self.res.broken_refs.append({"ref": "ann:" + key, "where": self.where})
                return f"[● annexure ‘{key}’ unresolved]"
            self.res.used_annexures.add(key)
            return f"Annexure {letter}"
        return key

    def runs(self, text: str) -> list[tuple[str, str | None]]:
        out: list[tuple[str, str | None]] = []
        text = REF.sub(lambda m: self._ref(m.group(1), m.group(2)), text)
        pos = 0
        for m in PH.finditer(text):
            if m.start() > pos:
                out.append((text[pos:m.start()], None))
            s, kind = self._fmt(m.group(1), m.group(2))
            out.append((s, kind))
            pos = m.end()
        if pos < len(text):
            out.append((text[pos:], None))
        return out

    # -------------------------------------------------- numbering pass
    def _number(self):
        for ai, art in enumerate(ARTICLES, 1):
            n = 0
            for cl in art.clauses:
                if not self._cond(cl.when):
                    continue
                n += 1
                num = f"{ai}.{n}"
                self.res.ref_map[cl.id] = num
                self._number_sub(cl, num, 1)

    def _number_sub(self, cl: C, num: str, depth: int):
        k = 0
        for s in cl.sub:
            if not self._cond(s.when):
                continue
            label = LETTERS[k] if depth == 1 else SMALL_ROMAN[k]
            k += 1
            snum = f"{num}({label})"
            self.res.ref_map[s.id] = snum
            self._number_sub(s, snum, depth + 1)

    # -------------------------------------------------- main
    def render(self, include_annexure_formats: bool = True) -> RenderResult:
        self._number()
        B = self.res.blocks
        d = self.data
        title_society = (schema.value(d, "society.name") or "[● SOCIETY]").upper()
        title_dev = (schema.value(d, "developer.name") or "[● DEVELOPER]").upper()
        B.append({"t": "cover", "title": "DEVELOPMENT AGREEMENT", "between": [title_society, title_dev],
                  "subtitle": "Redevelopment of the Property described in the First Schedule"})
        B.append({"t": "pagebreak"})
        B.append({"t": "toc", "items": [f"ARTICLE {a.num} – {a.title}" for a in ARTICLES] +
                  [f"{t} – {s}" for _k, t, s in self.schedules] +
                  [f"ANNEXURE {self.res.annexure_letters[k]} – {title}" for k, title, *_r in AX.ANNEXURES]})
        B.append({"t": "pagebreak"})
        B.append({"t": "heading", "text": "DEVELOPMENT AGREEMENT"})
        self.where = "Opening"
        B.append({"t": "para", "runs": self.runs(
            "THIS DEVELOPMENT AGREEMENT is made and entered into at {{exec.place}} on this ____ day of "
            "______________, 20__.")})
        B.append({"t": "center", "runs": [("BETWEEN", None)], "bold": True})
        for i, (label, text) in enumerate(PARTIES):
            self.where = f"Parties – {label.title()}"
            B.append({"t": "para", "runs": self.runs(text)})
            if i < len(PARTIES) - 1:
                B.append({"t": "center", "runs": [("AND", None)], "bold": True})
        B.append({"t": "para", "runs": [("The Society, the Developer and the Existing Members are hereinafter individually referred to as a “Party” and collectively as the “Parties”.", None)]})
        B.append({"t": "center", "runs": [("WHEREAS:", None)], "bold": True})
        letter = 0
        for rc in RECITALS:
            if not self._cond(rc.when):
                continue
            self.where = f"Recital {LETTERS[letter].upper()}"
            B.append({"t": "clause", "num": f"{LETTERS[letter].upper()}.", "level": 1, "runs": self.runs(rc.text), "id": rc.id})
            letter += 1
        B.append({"t": "para", "runs": [("NOW THIS AGREEMENT WITNESSETH AND IT IS HEREBY AGREED BY AND BETWEEN THE PARTIES AS FOLLOWS:", None)], "bold": True})

        for ai, art in enumerate(ARTICLES, 1):
            B.append({"t": "article", "num": art.num, "title": art.title})
            for cl in art.clauses:
                if not self._cond(cl.when):
                    continue
                self._emit_clause(cl, self.res.ref_map[cl.id], 1)

        B.append({"t": "para", "runs": [("[The Schedules and Annexures follow. Signatures appear at the end of this Agreement.]", None)], "italic": True})
        self._schedules()
        self._signatures()
        self._annexures(include_annexure_formats)
        self.res.full_text = "\n".join(_block_text(b) for b in B)
        return self.res

    def _emit_clause(self, cl: C, num: str, level: int):
        self.where = f"Clause {num}"
        if cl.text == "__DEFINITIONS__":
            self.res.blocks.append({"t": "clause", "num": num, "level": level, "heading": "Definitions.",
                                    "runs": [("The following terms shall have the meanings set out below:", None)], "id": cl.id})
            for dfn in sorted(DEFINITIONS, key=lambda x: re.sub(r"[^a-z0-9]", "", x.term.lower())):
                if not self._cond(dfn.when):
                    continue
                self.where = f"Clause {num} – definition of “{dfn.term}”"
                self.res.defined_terms.append(dfn.term)
                self.res.blocks.append({"t": "def", "term": dfn.term, "runs": self.runs(dfn.text)})
            return
        self.res.blocks.append({"t": "clause", "num": num if level == 1 else num[num.rfind("("):],
                                "level": level, "heading": cl.h, "runs": self.runs(cl.text), "id": cl.id,
                                "full_num": num})
        for s in cl.sub:
            if self._cond(s.when):
                self._emit_clause(s, self.res.ref_map[s.id], level + 1)

    # -------------------------------------------------- schedules
    def _sched_heading(self, key):
        for k, t, s in self.schedules:
            if k == key:
                self.res.blocks.append({"t": "pagebreak"})
                self.res.blocks.append({"t": "schedule", "title": t, "subtitle": s, "key": key})
                self.where = t.title()

    def _p(self, text, **kw):
        self.res.blocks.append({"t": "para", "runs": self.runs(text), **kw})

    def _table(self, header, rows, widths=None, total=False):
        self.res.blocks.append({"t": "table", "header": header, "rows": rows, "widths": widths, "total": total})

    def _missing_note(self, label, critical=True):
        self.res.outstanding.append({"key": f"schedule:{label}", "label": label, "where": self.where, "critical": critical, "status": "missing"})
        self.res.blocks.append({"t": "para", "runs": [(f"[● {label} – OUTSTANDING]", "missing")]})

    def _schedules(self):
        d, units = self.data, self.units
        # FIRST – property
        self._sched_heading("property")
        self._p("All that piece and parcel of land bearing Plot No. {{property.plot_no}}, Sector {{property.sector}}, "
                "{{property.node}}, {{property.city}}, admeasuring {{property.plot_area_sqm}} square metres or thereabouts, "
                "held by the Society on lease from CIDCO under the Lease Deed dated {{date:property.lease_deed_date}}, lying within "
                "the limits of {{property.authority}}, and bounded as follows:")
        self._table(["Direction", "Boundary"], [["On or towards the North", self._v("property.boundary_north")],
                                                ["On or towards the South", self._v("property.boundary_south")],
                                                ["On or towards the East", self._v("property.boundary_east")],
                                                ["On or towards the West", self._v("property.boundary_west")]], [35, 65])
        # SECOND – existing
        self._sched_heading("existing")
        self._p("{{property.existing_buildings}} standing on the Plot, constructed in or about {{property.construction_year}}, "
                "having an aggregate built-up area of {{property.existing_bua_sqm}} square metres, comprising "
                "{{num:property.units_count}} Existing Premises held by {{num:property.members_count}} registered members.")
        by_b: dict[str, list] = {}
        for u in units:
            by_b.setdefault(u.get("building") or "—", []).append(u)
        if units:
            rows = [[b, str(len(us)), indian_grouping(sum(to_float(x.get('existing_rera_carpet_sqft')) or 0 for x in us))]
                    for b, us in sorted(by_b.items())]
            self._table(["Building / Wing", "No. of Existing Premises", "Aggregate existing carpet (sq. ft.)"], rows, [40, 25, 35])
        else:
            self._missing_note("Member register (unit-wise particulars)")
        # THIRD – members
        self._sched_heading("members")
        if units:
            self._p("Note: The number of Existing Premises ({{property.units_count}}) and the number of registered members "
                    "({{property.members_count}}) are distinct. Areas are RERA Carpet Areas in square feet; balcony/terrace areas are stated separately.")
            rows = []
            for i, u in enumerate(units, 1):
                holders = " / ".join(_holder(h) for h in (u.get("holders") or [])) or "[● name OUTSTANDING]"
                ex, nw = to_float(u.get("existing_rera_carpet_sqft")), to_float(u.get("new_rera_carpet_sqft"))
                add = (nw - ex) if (ex is not None and nw is not None) else None
                rows.append([str(i), u.get("unit_no") or "", f"{u.get('building') or ''} {u.get('floor') or ''}".strip(), holders,
                             _a(ex), _a(u.get("existing_mofa_carpet_sqft")), _a(add), _a(nw), _a(u.get("balcony_sqft")),
                             u.get("parking") or (str(schema.value(d, 'tech.parking_per_unit') or '') + " car park")])
                if nw is None:
                    self.res.outstanding.append({"key": f"unit:{u.get('unit_no')}:new_area", "label": f"New RERA carpet area – unit {u.get('unit_no')}",
                                                 "where": self.where, "critical": True, "status": "missing"})
            rows.append(["", "TOTAL", "", f"{len(units)} units / {self.calc['members_from_register']} members",
                         _a(self.calc["existing_sqft_total"]), "", _a(self.calc["new_sqft_total"] - self.calc["existing_sqft_total"]),
                         _a(self.calc["new_sqft_total"]), "", ""])
            self._table(["Sr.", "Existing Unit", "Bldg / Floor", "Member(s)", "Existing RERA carpet", "Existing MOFA carpet",
                         "Additional free area", "New RERA carpet", "Balcony / terrace", "Parking"], rows,
                        [5, 9, 9, 22, 10, 9, 9, 10, 8, 9], total=True)
        else:
            self._missing_note("Member-wise area statement")
        # FOURTH – allocation
        self._sched_heading("allocation")
        types: dict[str, list] = {}
        for u in units:
            types.setdefault(u.get("unit_type") or "—", []).append(u)
        if units:
            rows = [[t, str(len(us)), _a(min((to_float(x.get('new_rera_carpet_sqft')) or 0) for x in us)),
                     str(sum(1 for x in us if x.get('use', 'Residential') == 'Residential'))] for t, us in sorted(types.items())]
            self._table(["Existing unit type", "No. of units", "Minimum new RERA carpet (sq. ft.)", "Residential units"], rows, [35, 15, 30, 20])
        self._p("Rehabilitation allocation: the Members’ New Premises shall be earmarked on the sanctioned plans and allotted by the Society "
                "by draw of lots in accordance with [[ref:ent_allocation]]. Parking allocation: {{num:tech.parking_per_unit}} car parking "
                "space(s) per Existing Premises, allotted by the Society in accordance with [[ref:ent_parking]]. Proposed building "
                "configuration: {{tech.building_config}}.")
        # FIFTH – financials
        self._sched_heading("financials")
        self._p("Rent basis: {{comm.rent_basis}}. Escalation: {{comm.rent_escalation_percent}} per cent every {{comm.rent_escalation_months}} months. "
                "Re-shifting charges: {{money:comm.reshifting}} per Existing Premises.")
        if units:
            rows = []
            for i, u in enumerate(units, 1):
                rows.append([str(i), u.get("unit_no") or "", " / ".join(_holder(h) for h in (u.get("holders") or [])),
                             _m(unit_rent(u, d)), _m(unit_amount(u, d, "deposit", "comm.deposit")),
                             _m(unit_amount(u, d, "brokerage", "comm.brokerage")), _m(unit_amount(u, d, "shifting", "comm.shifting")),
                             _m(unit_amount(u, d, "corpus", "comm.corpus")), _m(unit_amount(u, d, "hardship", "comm.hardship"))])
            c = self.calc
            rows.append(["", "TOTAL", "", _m(c["rent_total_month"]), _m(c["deposit_total"]), _m(c["brokerage_total"]),
                         _m(c["shifting_total"]), _m(c["corpus_total"]), _m(c["hardship_total"])])
            self._table(["Sr.", "Unit", "Member(s)", "Monthly Rent", "Deposit", "Brokerage", "Shifting", "Corpus", "Hardship"],
                        rows, [5, 9, 24, 11, 10, 10, 10, 11, 10], total=True)
            if any(unit_rent(u, d) is None for u in units):
                self._missing_note("Monthly Rent for one or more units (rent basis / rates)")
        else:
            self._missing_note("Member-wise financial statement")
        # SIXTH – amenities
        self._sched_heading("amenities")
        for key, label in (("tech.amenities", "Common Areas and Amenities"), ("tech.specifications", "Specifications of the Members’ New Premises")):
            self.res.blocks.append({"t": "subheading", "text": label})
            items = schema.value(d, key)
            if isinstance(items, str):
                items = [x.strip() for x in re.split(r"[;\n]", items) if x.strip()]
            if items:
                for i, it in enumerate(items, 1):
                    self.res.blocks.append({"t": "clause", "num": f"{i}.", "level": 1, "runs": [(str(it), "unverified" if (d.get(key) or {}).get("status") != "confirmed" else "fill")]})
            else:
                self._missing_note(label)
        # SEVENTH – BG
        self._sched_heading("bg")
        self._p("Bank Guarantee amount: {{money:security.bg_amount}}, to be furnished before the Vacation Notice in accordance with [[ref:bg]]. "
                "Each reduction requires the PMC’s written certificate under [[ref:bg_release]].")
        ms = schema.value(d, "security.bg_milestones")
        if ms:
            rows, tot = [], 0.0
            for i, m in enumerate(ms, 1):
                amt = to_float(m.get("amount")) if isinstance(m, dict) else None
                tot += amt or 0
                rows.append([str(i), m.get("milestone", "") if isinstance(m, dict) else str(m), _m(amt), "Before Vacation Notice",
                             "PMC certificate of milestone completion"])
            rows.append(["", "TOTAL", _m(tot), "", ""])
            self._table(["Sr.", "Release milestone", "Amount released", "Submission", "Evidence"], rows, [6, 38, 18, 18, 20], total=True)
            self.calc["bg_release_total"] = tot
        else:
            self._missing_note("Bank Guarantee release milestones")
        # EIGHTH – timeline
        self._sched_heading("timeline")
        rows = [
            ["Initial Approvals (CIDCO NOC, plan sanction, Commencement Certificate)", self._v("time.approval_months", "num", " months from this Agreement"), "Developer", "Approval letters; PMC certificate"],
            ["Registration of PAAAs", self._v("time.paaa_days", "num", " days from final draft PAAA"), "Existing Members / Developer", "Registered PAAAs"],
            ["Bank Guarantee", "Before Vacation Notice", "Developer", "Original BG lodged with Society"],
            ["Vacation of Existing Premises", self._v("time.vacation_notice_days", "num", " days from Valid Vacation Notice"), "Existing Members / Society", "Vacation undertakings"],
            ["Handover of Property", "7 days after vacation", "Society", "Handover memorandum (Annexure " + self.res.annexure_letters["possession_receipt"] + ")"],
            ["Completion and Full Occupation Certificate", self._v("time.construction_months", "num", " months from Handover Date"), "Developer", "Full OC; PMC certificate"],
            ["Grace period (Rent continues; LD thereafter)", self._v("time.grace_months", "num", " months"), "Developer", "—"],
            ["Long-Stop Date", self._v("time.longstop_months", "num", " months after Completion Date"), "Developer", "—"],
            ["Possession of Members’ New Premises", self._v("time.possession_take_days", "num", " days from Valid Possession Notice"), "Developer / Existing Members", "Possession letters"],
            ["Defect Liability Period", self._v("time.dlp_years", "num", " years from Possession Date"), "Developer", "Defect register"],
        ]
        self._table(["Milestone", "Time limit", "Responsible party", "Evidence"], rows, [36, 26, 18, 20])
        # NINTH – disclosures
        self._sched_heading("disclosures")
        self.res.blocks.append({"t": "subheading", "text": "Part A – Litigation affecting the Property"})
        self._p("{{property.litigation}}")
        self.res.blocks.append({"t": "subheading", "text": "Part B – Encumbrances on the Plot and dues"})
        self._p("{{property.encumbrances}}. Dues: {{property.cidco_dues}}.")
        self.res.blocks.append({"t": "subheading", "text": "Part C – Existing Premises mortgaged to banks / financial institutions"})
        mort = [[u.get("unit_no", ""), " / ".join(_holder(h) for h in u.get("holders") or []), u.get("mortgage"), u.get("bank_noc") or "NOC pending"]
                for u in units if u.get("mortgage")]
        self._table(["Unit", "Member(s)", "Lender", "NOC status"], mort or [["—", "None disclosed", "—", "—"]], [15, 40, 30, 15])
        self.res.blocks.append({"t": "subheading", "text": "Part D – Deceased members / pending transmission / transfer / disputes"})
        pend = [[u.get("unit_no", ""), " / ".join(_holder(h) for h in u.get("holders") or []), u.get("status"), u.get("notes") or ""]
                for u in units if (u.get("status") or "regular") != "regular" or any((h.get("status") or "") == "deceased" for h in u.get("holders") or [])]
        self._table(["Unit", "Recorded holder(s)", "Status", "Remarks"], pend or [["—", "None disclosed", "—", "—"]], [15, 40, 20, 25])
        self.res.blocks.append({"t": "subheading", "text": "Part E – Developer disclosures"})
        self._p("Litigation: {{developer.litigation}}. Insolvency: {{developer.insolvency}}.")

    def _v(self, key, fmt=None, suffix=""):
        s, _k = self._fmt(fmt, key)
        return s + (suffix if not s.startswith("[●") else "")

    def _signatures(self):
        B = self.res.blocks
        B.append({"t": "pagebreak"})
        B.append({"t": "para", "runs": [("IN WITNESS WHEREOF the Parties have set and subscribed their respective hands on the day and year first hereinabove written.", None)], "bold": True})
        self.where = "Execution"
        soc = [(schema.value(self.data, k) or f"[● {schema.FIELD_MAP[k].label} – OUTSTANDING]", r)
               for k, r in (("society.chairman", "Chairman"), ("society.secretary", "Secretary"), ("society.treasurer", "Treasurer"))]
        sig = schema.value(self.data, "developer.signatories") or "[● Authorised signatories – OUTSTANDING]"
        B.append({"t": "signatures", "blocks": [
            {"party": "SIGNED, SEALED AND DELIVERED by the within-named SOCIETY", "name": schema.value(self.data, "society.name") or "", "signers": soc},
            {"party": "SIGNED AND DELIVERED by the within-named DEVELOPER", "name": schema.value(self.data, "developer.name") or "", "signers": [(s.strip(), "Authorised Signatory") for s in re.split(r",| and ", sig) if s.strip()]},
            {"party": "SIGNED AND DELIVERED by the within-named EXISTING MEMBERS (as per the Third Schedule, on the following pages / by separate Deeds of Confirmation)", "name": "", "signers": []},
        ]})
        B.append({"t": "witness"})

    def _annexures(self, include_formats: bool):
        for k, title, kind, doc_types in AX.ANNEXURES:
            letter = self.res.annexure_letters[k]
            self.res.blocks.append({"t": "pagebreak"})
            self.res.blocks.append({"t": "annexure", "letter": letter, "title": title, "key": k})
            self.where = f"Annexure {letter}"
            if kind == "copy":
                have = [x for x in self.docs if x.get("doc_type") in doc_types]
                if have:
                    self.res.blocks.append({"t": "para", "runs": [(f"[Copy of {have[0]['filename']} (uploaded document) to be annexed at execution.]", None)], "italic": True})
                else:
                    self._missing_note(f"Document for Annexure {letter} ({title})", critical=False)
            elif include_formats:
                for para in AX.ANNEXURE_FORMATS[k]:
                    if para.startswith("## "):
                        self.res.blocks.append({"t": "center", "runs": self.runs(para[3:]), "bold": True})
                    else:
                        for line in para.split("\n\n"):
                            self.res.blocks.append({"t": "para", "runs": self.runs(line)})


def _holder(h: dict) -> str:
    n = h.get("name", "")
    if (h.get("status") or "") == "deceased":
        n = "Late " + n
    if h.get("share"):
        n += f" ({h['share']})"
    return n


def _a(v) -> str:
    f = to_float(v)
    return "" if f is None else (f"{f:,.2f}".rstrip("0").rstrip("."))


def _m(v) -> str:
    return "[● outstanding]" if v is None else money_short(v)


def _block_text(b: dict) -> str:
    if "runs" in b:
        prefix = (b.get("num", "") + " ") if b.get("num") else ""
        if b.get("t") == "def":
            prefix = f"“{b['term']}” "
        return prefix + (b.get("heading") or "") + " " + "".join(t for t, _ in b["runs"])
    if b["t"] == "table":
        return "\n".join(" | ".join(map(str, r)) for r in [b["header"]] + b["rows"])
    if b["t"] in ("article",):
        return f"ARTICLE {b['num']} {b['title']}"
    if b["t"] in ("schedule",):
        return f"{b['title']} {b['subtitle']}"
    return ""


def render_project(data: dict, units: list[dict], docs: list[dict] | None = None) -> RenderResult:
    return Renderer(data, units, docs).render()
