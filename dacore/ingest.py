"""Document readers (DOCX, PDF, scanned PDF via OCR, XLSX/CSV, images) and classification.

Every reader returns segments: {"page": int, "para": int, "text": str, "kind": "text"|"table_row"}
and tables: [{"page": int, "rows": [[cell,...],...]}]. Page/paragraph numbers become the
source references for every extracted fact.
"""
from __future__ import annotations

import csv
import io
import re
import zipfile
from dataclasses import dataclass, field

_OCR = None


def _ocr_engine():
    global _OCR
    if _OCR is None:
        from rapidocr_onnxruntime import RapidOCR
        _OCR = RapidOCR()
    return _OCR


def ocr_image_bytes(data: bytes) -> list[str]:
    import numpy as np
    from PIL import Image
    img = Image.open(io.BytesIO(data)).convert("RGB")
    result, _ = _ocr_engine()(np.array(img))
    if not result:
        return []
    # group boxes into lines by vertical position
    items = sorted(((b[0][0][1], b[0][0][0], b[1]) for b in result), key=lambda x: (round(x[0] / 12), x[1]))
    lines, cur, cur_y = [], [], None
    for y, x, t in items:
        if cur_y is None or abs(y - cur_y) < 12:
            cur.append(t); cur_y = y if cur_y is None else cur_y
        else:
            lines.append(" ".join(cur)); cur, cur_y = [t], y
    if cur:
        lines.append(" ".join(cur))
    return lines


@dataclass
class Parsed:
    segments: list[dict] = field(default_factory=list)
    tables: list[dict] = field(default_factory=list)
    pages: int = 0
    ocr_used: bool = False
    warnings: list[str] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "\n".join(s["text"] for s in self.segments)


def read_docx(data: bytes) -> Parsed:
    from lxml import etree
    W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    p = Parsed(pages=1)
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        root = etree.fromstring(z.read("word/document.xml"))
    body = root.find(W + "body")
    page, para = 1, 0

    def txt(el):
        out = []
        for e in el.iter(W + "t", W + "tab", W + "br"):
            if e.tag == W + "t":
                out.append(e.text or "")
            elif e.tag == W + "tab":
                out.append("\t")
        return "".join(out)

    for el in body:
        if el.tag == W + "p":
            if el.findall(".//" + W + "br[@" + W + "type='page']") or el.find(W + "pPr/" + W + "pageBreakBefore") is not None:
                page += 1
            t = txt(el).strip()
            if t:
                para += 1
                p.segments.append({"page": page, "para": para, "text": t, "kind": "text"})
        elif el.tag == W + "tbl":
            rows = []
            for tr in el.iter(W + "tr"):
                cells = [txt(tc).strip() for tc in tr.findall(W + "tc")]
                rows.append(cells)
                para += 1
                p.segments.append({"page": page, "para": para, "text": " | ".join(cells), "kind": "table_row"})
            p.tables.append({"page": page, "rows": rows})
    p.pages = page
    return p


def read_pdf(data: bytes) -> Parsed:
    import pymupdf as fitz
    p = Parsed()
    doc = fitz.open(stream=data, filetype="pdf")
    p.pages = doc.page_count
    for i, page in enumerate(doc, 1):
        text = page.get_text("text") or ""
        if len(text.strip()) < 25:  # scanned page -> OCR
            pix = page.get_pixmap(dpi=200)
            lines = ocr_image_bytes(pix.tobytes("png"))
            p.ocr_used = True
            for j, ln in enumerate(lines, 1):
                if ln.strip():
                    p.segments.append({"page": i, "para": j, "text": ln.strip(), "kind": "text", "ocr": True})
            continue
        blocks = [b[4] for b in sorted(page.get_text("blocks"), key=lambda b: (round(b[1]), b[0])) if b[6] == 0 and b[4].strip()]
        for j, blk in enumerate(blocks, 1):
            t = re.sub(r"\s*\n\s*", " ", blk).strip()
            if t:
                p.segments.append({"page": i, "para": j, "text": t, "kind": "text"})
    try:  # tables
        import pdfplumber
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            for i, pg in enumerate(pdf.pages, 1):
                for tb in pg.extract_tables() or []:
                    rows = [[(c or "").strip() for c in r] for r in tb]
                    if len(rows) > 1:
                        p.tables.append({"page": i, "rows": rows})
    except Exception as e:  # pragma: no cover
        p.warnings.append(f"table extraction failed: {e}")
    return p


def read_xlsx(data: bytes) -> Parsed:
    import openpyxl
    p = Parsed()
    wb = openpyxl.load_workbook(io.BytesIO(data), data_only=True, read_only=True)
    for si, ws in enumerate(wb.worksheets, 1):
        rows = []
        for ri, row in enumerate(ws.iter_rows(values_only=True), 1):
            cells = ["" if v is None else str(v).strip() for v in row]
            if any(cells):
                rows.append(cells)
                p.segments.append({"page": si, "para": ri, "text": " | ".join(cells), "kind": "table_row", "sheet": ws.title})
        if rows:
            p.tables.append({"page": si, "rows": rows, "sheet": ws.title})
    p.pages = len(wb.worksheets)
    return p


def read_csv(data: bytes) -> Parsed:
    p = Parsed(pages=1)
    rows = [r for r in csv.reader(io.StringIO(data.decode("utf-8-sig", errors="replace"))) if any(c.strip() for c in r)]
    for i, r in enumerate(rows, 1):
        p.segments.append({"page": 1, "para": i, "text": " | ".join(r), "kind": "table_row"})
    p.tables.append({"page": 1, "rows": rows})
    return p


def read_image(data: bytes) -> Parsed:
    p = Parsed(pages=1, ocr_used=True)
    for j, ln in enumerate(ocr_image_bytes(data), 1):
        p.segments.append({"page": 1, "para": j, "text": ln, "kind": "text", "ocr": True})
    return p


def read_any(filename: str, data: bytes) -> Parsed:
    ext = filename.lower().rsplit(".", 1)[-1]
    if ext == "docx":
        return read_docx(data)
    if ext == "pdf":
        return read_pdf(data)
    if ext in ("xlsx", "xlsm"):
        return read_xlsx(data)
    if ext == "csv":
        return read_csv(data)
    if ext in ("png", "jpg", "jpeg", "tif", "tiff", "bmp", "webp"):
        return read_image(data)
    if ext in ("txt", "md"):
        p = Parsed(pages=1)
        for i, ln in enumerate(data.decode("utf-8", errors="replace").splitlines(), 1):
            if ln.strip():
                p.segments.append({"page": 1, "para": i, "text": ln.strip(), "kind": "text"})
        return p
    raise ValueError(f"Unsupported file type: .{ext}")


# ------------------------------------------------------------------ classification
DOC_TYPES = [  # (doc_type, category, label, keyword patterns)
    ("society_registration", "society", "Society registration certificate", [r"certificate of registration", r"registered under .*co-?operative societies act", r"registration no"]),
    ("bye_laws", "society", "Bye-laws", [r"bye-?laws"]),
    ("sgbm_minutes", "society", "SGBM notice / minutes", [r"special general body meeting", r"\bsgbm\b", r"minutes of"]),
    ("order_79a", "society", "Section 79A order / Deputy Registrar correspondence", [r"79\s*\(?a\)?", r"deputy registrar"]),
    ("pmc_appointment", "society", "PMC appointment", [r"project management consultant", r"appointment of pmc"]),
    ("tender", "society", "Tender notice / document", [r"tender", r"invitation for offers"]),
    ("evaluation_report", "society", "Comparative evaluation report", [r"comparative", r"evaluation report", r"bid evaluation"]),
    ("final_offer", "developer", "Developer final offer", [r"final offer", r"no regret offer", r"offer letter", r"our offer"]),
    ("appointment_letter", "society", "Developer appointment letter", [r"letter of appointment", r"appoint(ed)? you as (the )?developer"]),
    ("lease_deed", "property", "CIDCO Lease Deed", [r"lease deed", r"lessor", r"lessee", r"demise"]),
    ("agreement_to_lease", "property", "Agreement to Lease", [r"agreement to lease"]),
    ("cidco_noc", "property", "CIDCO NOC", [r"no objection", r"\bnoc\b"]),
    ("structural_audit", "property", "Structural audit report", [r"structural audit", r"\bc-?[123]\b category", r"dilapidated"]),
    ("property_tax", "property", "Property tax / dues", [r"property tax", r"assessment"]),
    ("member_register", "members", "Member register", [r"share certificate", r"flat no", r"member name", r"name of (the )?member"]),
    ("developer_incorporation", "developer", "Certificate of Incorporation", [r"certificate of incorporation", r"\bcin\b"]),
    ("developer_board_resolution", "developer", "Board resolution", [r"board of directors", r"board resolution", r"resolved that"]),
    ("developer_financials", "developer", "Financial statements / net-worth", [r"net[- ]?worth", r"balance sheet", r"turnover", r"solvency"]),
    ("feasibility", "technical", "Feasibility report / FSI calculation", [r"feasibility", r"\bfsi\b", r"floor space index", r"area statement"]),
    ("area_statement", "technical", "Architect area statement", [r"area statement", r"architect"]),
    ("plans", "technical", "Plans / drawings", [r"sanctioned plan", r"proposed plan", r"layout plan"]),
    ("amenities", "technical", "Amenities and specifications", [r"amenities", r"specifications"]),
    ("development_agreement", "review", "Development Agreement", [r"development agreement", r"redevelopment agreement"]),
]
DOC_TYPE_LABELS = {d[0]: d[2] for d in DOC_TYPES}


def classify(filename: str, text: str, category_hint: str | None = None) -> str:
    sample = (filename + "\n" + text[:6000]).lower()
    best, score = "unclassified", 0
    for dt, cat, _lbl, pats in DOC_TYPES:
        s = sum(len(re.findall(p, sample)) for p in pats)
        if category_hint and cat == category_hint:
            s *= 1.5
        if s > score:
            best, score = dt, s
    # long documents that call themselves agreements are DAs regardless of keyword noise
    if re.search(r"(re-?)?development agreement", sample) and len(text) > 30000:
        best = "development_agreement"
    return best
