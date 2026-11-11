"""Review output reports (Word / Excel)."""
from __future__ import annotations

import datetime as dt
import io

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

from ..config import FIRM_LEGAL, FIRM_PMC

SEV_COLOR = {"Critical": "C00000", "High": "E36C09", "Medium": "BF9000", "Low": "548235"}


def _doc(title: str, subtitle: str, landscape=False) -> Document:
    d = Document()
    st = d.styles["Normal"]; st.font.name = "Calibri"; st.font.size = Pt(10)
    s = d.sections[0]
    s.page_height, s.page_width = Cm(29.7), Cm(21.0)
    if landscape:
        s.orientation = WD_ORIENT.LANDSCAPE
        s.page_width, s.page_height = Cm(29.7), Cm(21.0)
    for side in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
        setattr(s, side, Cm(1.8))
    p = d.add_paragraph(); r = p.add_run(title); r.bold = True; r.font.size = Pt(16)
    d.add_paragraph(subtitle)
    p = d.add_paragraph(f"Prepared by {FIRM_LEGAL} with {FIRM_PMC} · {dt.date.today():%d %B %Y}")
    p.runs[0].italic = True; p.runs[0].font.size = Pt(8.5)
    p = d.add_paragraph("Privileged and confidential – prepared for the Society. Statutory references are to be verified by the advocate against the current text before reliance.")
    p.runs[0].font.size = Pt(8); p.runs[0].font.color.rgb = RGBColor(0x80, 0x80, 0x80)
    return d


def _shade(cell, fill):
    tcPr = cell._tc.get_or_add_tcPr(); shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear"); shd.set(qn("w:color"), "auto"); shd.set(qn("w:fill"), fill); tcPr.append(shd)


def _table(d, header, rows, widths=None, sev_col=None):
    t = d.add_table(rows=1, cols=len(header)); t.style = "Table Grid"
    for i, h in enumerate(header):
        c = t.rows[0].cells[i]; c.text = ""; r = c.paragraphs[0].add_run(h); r.bold = True; r.font.size = Pt(9); _shade(c, "1F3864")
        r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
    for row in rows:
        cells = t.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = ""
            r = cells[i].paragraphs[0].add_run(str(v if v is not None else "")); r.font.size = Pt(8.5)
            if sev_col is not None and i == sev_col and v in SEV_COLOR:
                _shade(cells[i], SEV_COLOR[v]); r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF); r.bold = True
    if widths:
        for row in t.rows:
            for i, w in enumerate(widths):
                row.cells[i].width = Cm(w)
    d.add_paragraph()
    return t


def _bytes(d) -> bytes:
    from ..drafting.docx_builder import fix_settings
    fix_settings(d)
    b = io.BytesIO(); d.save(b); return b.getvalue()


def legal_review_report(findings: list[dict], title: str, stats: dict) -> bytes:
    d = _doc("Legal Review Report", f"Development Agreement reviewed: {title}")
    counts = {s: sum(1 for f in findings if f["severity"] == s) for s in SEV_COLOR}
    d.add_heading("1. Summary", level=2)
    d.add_paragraph(f"{len(findings)} issues identified – Critical {counts['Critical']}, High {counts['High']}, Medium {counts['Medium']}, Low {counts['Low']}. "
                    f"The redlined draft contains {stats.get('insertions', 0)} tracked insertions, {stats.get('deletions', 0)} tracked deletions and "
                    f"{stats.get('comments', 0)} explanatory comments. Clauses not mentioned in this report were found satisfactory and have been retained unchanged.")
    for cat in ["Legal", "Commercial", "Construction", "Society Protection", "Missing Clause"]:
        fs = [f for f in findings if f["category"] == cat]
        if not fs:
            continue
        d.add_heading(f"{cat} review", level=2)
        for f in fs:
            p = d.add_paragraph(); r = p.add_run(f"{f['id']} · {f['title']}"); r.bold = True
            r2 = p.add_run(f"   [{f['severity']} · {'Negotiable' if f['negotiable'] else 'Mandatory'} · {f['clause_ref']} · {f['status']}]"); r2.font.size = Pt(8.5)
            for lbl, key in (("Original wording", "original"), ("Proposed wording", "proposed"), ("Reason for amendment", "reason"),
                             ("Society's benefit", "benefit"), ("Risk addressed", "risk"), ("Legal reference", "legal"), ("Note", "note")):
                if f.get(key):
                    q = d.add_paragraph(style="List Bullet"); a = q.add_run(lbl + ": "); a.bold = True; q.add_run(f[key])
    return _bytes(d)


def missing_clauses_report(findings: list[dict], title: str) -> bytes:
    d = _doc("Missing Clauses Report", f"Important provisions absent from: {title}")
    fs = [f for f in findings if f["kind"] == "insertion"]
    if not fs:
        d.add_paragraph("No essential provision was found to be missing.")
    _table(d, ["Ref", "Missing provision", "Severity", "Inserted after", "Proposed clause (tracked insertion)", "Why it is needed"],
           [[f["id"], f["title"], f["severity"], f["clause_ref"], f["proposed"], f["reason"] + " " + f["risk"]] for f in fs],
           [1.2, 3, 1.8, 2.5, 6, 3.5], sev_col=2)
    return _bytes(d)


def clause_comparison(findings: list[dict], title: str) -> bytes:
    d = _doc("Clause Comparison", f"Original clause v. proposed clause – {title}", landscape=True)
    _table(d, ["Ref", "Clause", "Original", "Proposed", "Mandatory / Negotiable", "Status"],
           [[f["id"], f["clause_ref"], f["original"], f["proposed"], "Negotiable" if f["negotiable"] else "Mandatory", f["status"]] for f in findings],
           [1.2, 2.5, 9, 9, 2.5, 1.8])
    return _bytes(d)


def negotiation_report(findings: list[dict], title: str) -> bytes:
    d = _doc("Negotiation Report", f"Clauses requiring discussion with the Developer – {title}")
    neg = [f for f in findings if f["negotiable"] or f["kind"] == "comment"]
    mand = [f for f in findings if not (f["negotiable"] or f["kind"] == "comment") and f["severity"] in ("Critical", "High")]
    d.add_heading("A. Non-negotiable Society protections (to be insisted upon)", level=2)
    _table(d, ["Ref", "Issue", "Severity", "Clause", "Society position"], [[f["id"], f["title"], f["severity"], f["clause_ref"], f["benefit"]] for f in mand], [1.2, 5, 1.8, 3, 7], sev_col=2)
    d.add_heading("B. Negotiable points", level=2)
    _table(d, ["Ref", "Issue", "Severity", "Clause", "Recommended position"], [[f["id"], f["title"], f["severity"], f["clause_ref"], f["reason"]] for f in neg], [1.2, 5, 1.8, 3, 7], sev_col=2)
    return _bytes(d)


def execution_checklist_report(items: list[dict], title: str) -> bytes:
    d = _doc("Execution Checklist", f"Missing documents, schedules, annexures, blanks and approvals – {title}")
    std = ["Certified copy of SGBM resolution approving the final DA", "Deputy Registrar 79A order", "Developer board resolution / partner authority",
           "Developer KYC: PAN, CIN, GST, constitution documents", "Net-worth, solvency and banker certificates", "Litigation and insolvency disclosure affidavit",
           "Final member list with unit-wise carpet areas (Society + PMC verified)", "Amenities and specifications annexure", "Bank guarantee draft vetted by the bank",
           "PAAA draft", "Power of attorney draft (limited, co-terminus)", "Stamp duty assessment and registration appointment"]
    d.add_heading("A. Defects found in the draft", level=2)
    _table(d, ["#", "Type", "Where", "Detail"], [[i + 1, x["type"], x["where"], x["detail"]] for i, x in enumerate(items)], [1, 4, 3.5, 9])
    d.add_heading("B. Standard pre-execution checklist", level=2)
    _table(d, ["#", "Item", "Status"], [[i + 1, s, "☐ pending"] for i, s in enumerate(std)], [1, 12, 4])
    return _bytes(d)


def risk_matrix_xlsx(findings: list[dict], title: str) -> bytes:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    wb = Workbook(); ws = wb.active; ws.title = "Society Risk Matrix"
    ws.append([f"Society Risk Matrix – {title}"]); ws["A1"].font = Font(bold=True, size=14)
    ws.append([])
    hdr = ["Ref", "Rule", "Risk level", "Category", "Issue", "Clause", "Risk addressed", "Society benefit", "Mandatory / Negotiable", "Status"]
    ws.append(hdr)
    for c in ws[3]:
        c.font = Font(bold=True, color="FFFFFF"); c.fill = PatternFill("solid", fgColor="1F3864")
    for f in findings:
        ws.append([f["id"], f["rule"], f["severity"], f["category"], f["title"], f["clause_ref"], f["risk"], f["benefit"],
                   "Negotiable" if f["negotiable"] else "Mandatory", f["status"]])
        cell = ws.cell(row=ws.max_row, column=3)
        cell.fill = PatternFill("solid", fgColor=SEV_COLOR.get(f["severity"], "FFFFFF")); cell.font = Font(bold=True, color="FFFFFF")
    for col, w in zip("ABCDEFGHIJ", [7, 9, 10, 16, 42, 22, 40, 40, 14, 10]):
        ws.column_dimensions[col].width = w
    for row in ws.iter_rows(min_row=4):
        for c in row:
            c.alignment = Alignment(wrap_text=True, vertical="top")
    ws.freeze_panes = "A4"
    s2 = wb.create_sheet("Summary")
    s2.append(["Category", "Critical", "High", "Medium", "Low", "Total"])
    for cat in sorted({f["category"] for f in findings}):
        fs = [f for f in findings if f["category"] == cat]
        s2.append([cat] + [sum(1 for f in fs if f["severity"] == s) for s in ("Critical", "High", "Medium", "Low")] + [len(fs)])
    b = io.BytesIO(); wb.save(b); return b.getvalue()


def validation_report(checks: list[dict], outstanding: list[dict], unverified: list[dict], title: str) -> bytes:
    d = _doc("Clause Consistency & Validation Report", title)
    fails = [c for c in checks if c["status"] != "pass"]
    d.add_paragraph(f"{len(checks)} checks run · {sum(c['status']=='pass' for c in checks)} passed · "
                    f"{sum(c['status']=='fail' for c in checks)} failed · {sum(c['status']=='warn' for c in checks)} warnings.")
    d.add_heading("Issues", level=2)
    _table(d, ["Check", "Category", "Severity", "Result", "Detail"], [[c["id"], c["category"], c["severity"].title(), c["status"].upper(), c["message"]] for c in fails],
           [3.5, 2.5, 1.8, 1.5, 8])
    d.add_heading("Outstanding information (marked [●] in the draft)", level=2)
    _table(d, ["Field", "Critical", "Status", "Where in draft"], [[o["label"], "Yes" if o["critical"] else "", o.get("status", ""), o["where"]] for o in outstanding], [6, 1.5, 2.5, 7])
    d.add_heading("Extracted information awaiting verification (turquoise in the draft)", level=2)
    _table(d, ["Field", "Value used", "Where"], [[u["label"], u["value"], u["where"]] for u in unverified], [6, 6, 5])
    d.add_heading("Passed checks", level=2)
    _table(d, ["Check", "Detail"], [[c["id"], c["message"]] for c in checks if c["status"] == "pass"], [4, 13])
    return _bytes(d)
