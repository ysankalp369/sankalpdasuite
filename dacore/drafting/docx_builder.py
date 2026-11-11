"""Word (.docx) writer for the document model produced by render.py.

A4, legal typography, bold article headings, hanging-indent clause numbering, schedules,
annexure dividers, page X of Y footer with initials box, signature and witness blocks.
"""
from __future__ import annotations

import io

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_COLOR_INDEX
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

FONT = "Times New Roman"


def _field(run, instr: str):
    f1 = OxmlElement("w:fldChar"); f1.set(qn("w:fldCharType"), "begin")
    it = OxmlElement("w:instrText"); it.set(qn("xml:space"), "preserve"); it.text = instr
    f2 = OxmlElement("w:fldChar"); f2.set(qn("w:fldCharType"), "separate")
    t = OxmlElement("w:t"); t.text = "1"
    f3 = OxmlElement("w:fldChar"); f3.set(qn("w:fldCharType"), "end")
    for el in (f1, it, f2, t, f3):
        run._r.append(el)


def _shade(cell, hex_fill: str):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd"); shd.set(qn("w:val"), "clear"); shd.set(qn("w:color"), "auto"); shd.set(qn("w:fill"), hex_fill)
    tcPr.append(shd)


def _styles(doc: Document):
    st = doc.styles
    normal = st["Normal"]
    normal.font.name = FONT
    normal.font.size = Pt(11.5)
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    pf = normal.paragraph_format
    pf.space_after = Pt(6); pf.line_spacing = 1.3
    pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    from docx.enum.style import WD_STYLE_TYPE
    def add(name, base="Normal"):
        s = st.add_style(name, WD_STYLE_TYPE.PARAGRAPH); s.base_style = st[base]; return s
    a = add("DA Article"); a.font.bold = True; a.font.size = Pt(12); a.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    a.paragraph_format.space_before = Pt(14); a.paragraph_format.keep_with_next = True
    for lvl, (left, hang) in enumerate([(1.25, 1.25), (2.25, 1.0), (3.1, 0.85)], 1):
        s = add(f"DA Clause {lvl}")
        s.paragraph_format.left_indent = Cm(left); s.paragraph_format.first_line_indent = Cm(-hang)
        s.paragraph_format.tab_stops.add_tab_stop(Cm(left))
    d = add("DA Definition"); d.paragraph_format.left_indent = Cm(1.25)
    sh = add("DA Schedule"); sh.font.bold = True; sh.font.size = Pt(12.5); sh.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sh.paragraph_format.keep_with_next = True
    tc = add("DA Table"); tc.font.size = Pt(9); tc.paragraph_format.space_after = Pt(0); tc.paragraph_format.line_spacing = 1.0
    tc.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT


def _add_runs(p, runs, bold=False, italic=False):
    for text, kind in runs:
        r = p.add_run(text)
        r.bold = bold or kind == "b"
        r.italic = italic
        if kind == "missing":
            r.bold = True
            r.font.highlight_color = WD_COLOR_INDEX.YELLOW
            r.font.color.rgb = RGBColor(0xA0, 0x00, 0x00)
        elif kind == "unverified":
            r.font.highlight_color = WD_COLOR_INDEX.TURQUOISE


def _footer(section, title):
    hp = section.header.paragraphs[0]
    hp.text = title; hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    for r in hp.runs:
        r.font.size = Pt(8); r.italic = True
    fp = section.footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = fp.add_run("Society: ________        Developer: ________                Page "); r.font.size = Pt(8.5)
    r = fp.add_run(); r.font.size = Pt(8.5); _field(r, "PAGE")
    r = fp.add_run(" of "); r.font.size = Pt(8.5)
    r = fp.add_run(); r.font.size = Pt(8.5); _field(r, "NUMPAGES")


def build_docx(blocks: list[dict], header_title: str, draft_banner: str | None = None) -> bytes:
    doc = Document()
    _styles(doc)
    sec = doc.sections[0]
    sec.page_height, sec.page_width = Cm(29.7), Cm(21.0)
    sec.orientation = WD_ORIENT.PORTRAIT
    sec.top_margin, sec.bottom_margin = Cm(2.5), Cm(2.2)
    sec.left_margin, sec.right_margin = Cm(3.0), Cm(2.2)
    _footer(sec, header_title)
    body_width_cm = 21.0 - 3.0 - 2.2

    for b in blocks:
        t = b["t"]
        if t == "cover":
            for _ in range(5):
                doc.add_paragraph()
            if draft_banner:
                p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                r = p.add_run(draft_banner); r.bold = True; r.font.color.rgb = RGBColor(0xB0, 0, 0); r.font.size = Pt(11)
            p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = p.add_run(b["title"]); r.bold = True; r.font.size = Pt(22)
            p = doc.add_paragraph(b["subtitle"]); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            doc.add_paragraph()
            for i, name in enumerate(b["between"]):
                p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                r = p.add_run(name); r.bold = True; r.font.size = Pt(14)
                if i < len(b["between"]) - 1:
                    p = doc.add_paragraph("AND"); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p = doc.add_paragraph("AND THE EXISTING MEMBERS NAMED IN THE THIRD SCHEDULE"); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        elif t == "pagebreak":
            doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
        elif t == "toc":
            p = doc.add_paragraph("TABLE OF CONTENTS", style="DA Article")
            for it in b["items"]:
                q = doc.add_paragraph(it); q.paragraph_format.space_after = Pt(1); q.alignment = WD_ALIGN_PARAGRAPH.LEFT
                for r in q.runs: r.font.size = Pt(10)
        elif t == "heading":
            p = doc.add_paragraph(style="DA Article"); r = p.add_run(b["text"]); r.font.size = Pt(15)
        elif t == "center":
            p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            _add_runs(p, b["runs"], bold=b.get("bold", False))
        elif t == "para":
            p = doc.add_paragraph()
            _add_runs(p, b["runs"], bold=b.get("bold", False), italic=b.get("italic", False))
        elif t == "article":
            p = doc.add_paragraph(style="DA Article"); p.add_run(f"ARTICLE {b['num']}")
            p2 = doc.add_paragraph(style="DA Article"); p2.paragraph_format.space_before = Pt(0); p2.add_run(b["title"])
        elif t == "clause":
            lvl = min(b.get("level", 1), 3)
            p = doc.add_paragraph(style=f"DA Clause {lvl}")
            p.add_run(f"{b['num']}\t")
            if b.get("heading"):
                hr = p.add_run(b["heading"] + " "); hr.bold = True
            _add_runs(p, b["runs"])
        elif t == "def":
            p = doc.add_paragraph(style="DA Definition")
            r = p.add_run(f"“{b['term']}” "); r.bold = True
            _add_runs(p, b["runs"])
        elif t == "schedule":
            doc.add_paragraph(b["title"], style="DA Schedule")
            p = doc.add_paragraph(f"({b['subtitle']})", style="DA Schedule"); p.runs[0].bold = False
        elif t == "subheading":
            p = doc.add_paragraph(); r = p.add_run(b["text"]); r.bold = True; r.underline = True
        elif t == "annexure":
            for _ in range(2):
                doc.add_paragraph()
            p = doc.add_paragraph(f"ANNEXURE {b['letter']}", style="DA Schedule")
            doc.add_paragraph(b["title"], style="DA Schedule").runs[0].bold = False
        elif t == "table":
            _table(doc, b, body_width_cm)
        elif t == "signatures":
            for blk in b["blocks"]:
                p = doc.add_paragraph(); r = p.add_run(blk["party"]); r.bold = True
                if blk["name"]:
                    doc.add_paragraph(blk["name"].upper())
                if blk["signers"]:
                    tb = doc.add_table(rows=1, cols=4); tb.style = "Table Grid"
                    for i, h in enumerate(["Name and designation", "Signature", "Photograph", "Left thumb impression"]):
                        tb.rows[0].cells[i].text = h; _shade(tb.rows[0].cells[i], "E7E6E6")
                    for name, role in blk["signers"]:
                        row = tb.add_row(); row.height = Cm(2.4)
                        row.cells[0].text = f"{name}\n({role})"
                    doc.add_paragraph()
        elif t == "witness":
            p = doc.add_paragraph(); r = p.add_run("In the presence of witnesses:"); r.bold = True
            for i in (1, 2):
                doc.add_paragraph(f"{i}. Name: ______________________  Address: ______________________  Signature: __________")
    fix_settings(doc)
    bio = io.BytesIO()
    doc.save(bio)
    return bio.getvalue()


def fix_settings(doc):
    """python-docx's default template omits the schema-required w:percent on w:zoom."""
    z = doc.settings.element.find(qn("w:zoom"))
    if z is not None and z.get(qn("w:percent")) is None:
        z.set(qn("w:percent"), "100")


def _table(doc, b, body_width_cm):
    cols = len(b["header"])
    tb = doc.add_table(rows=1, cols=cols)
    tb.style = "Table Grid"; tb.alignment = WD_TABLE_ALIGNMENT.CENTER
    widths = b.get("widths") or [100 / cols] * cols
    for i, h in enumerate(b["header"]):
        c = tb.rows[0].cells[i]; c.text = ""
        p = c.paragraphs[0]; p.style = doc.styles["DA Table"]; r = p.add_run(str(h)); r.bold = True
        _shade(c, "D9E2F3")
    # repeat header row on each page
    trPr = tb.rows[0]._tr.get_or_add_trPr(); th = OxmlElement("w:tblHeader"); th.set(qn("w:val"), "true"); trPr.append(th)
    for ri, row in enumerate(b["rows"]):
        cells = tb.add_row().cells
        is_total = b.get("total") and ri == len(b["rows"]) - 1
        for i in range(cols):
            v = str(row[i]) if i < len(row) and row[i] is not None else ""
            p = cells[i].paragraphs[0]; p.style = doc.styles["DA Table"]
            r = p.add_run(v); r.bold = bool(is_total)
            if "[●" in v:
                r.font.highlight_color = WD_COLOR_INDEX.YELLOW; r.bold = True
    for row in tb.rows:
        for i, w in enumerate(widths):
            row.cells[i].width = Cm(body_width_cm * w / sum(widths))
    doc.add_paragraph()
