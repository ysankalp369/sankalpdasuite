"""Genuine Microsoft Word tracked-changes engine (WordprocessingML revision markup).

* Deletions are wrapped in <w:del> with <w:delText>; insertions in <w:ins>; each carries
  w:id / w:author / w:date. The original run properties (rPr) are preserved, so formatting,
  numbering (pPr/numPr) and cross-references are untouched.
* New clauses are inserted as new paragraphs whose paragraph mark is itself tracked
  (<w:pPr><w:rPr><w:ins/></w:rPr></w:pPr>) and which clone the anchor paragraph's pPr.
* Comments are written to word/comments.xml (created if absent) and anchored with
  commentRangeStart / commentRangeEnd / commentReference.
* Only runs that are direct children of a paragraph are edited. Text inside existing revisions,
  hyperlinks, fields or content controls is treated as locked: an edit touching it is refused
  (and reported) rather than risking a corrupted document.
"""
from __future__ import annotations

import copy
import datetime as dt
import io
import re
import zipfile
from dataclasses import dataclass, field

from lxml import etree

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W = "{%s}" % W_NS
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
COMMENTS_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments"
COMMENTS_CT = "application/vnd.openxmlformats-officedocument.wordprocessingml.comments+xml"


@dataclass
class Edit:
    """Replace paragraph text[start:end] with `new` (empty = pure deletion; start==end = pure insertion)."""
    para: int
    start: int
    end: int
    new: str
    comment: str = ""
    finding_id: str = ""
    delete_mark: bool = False   # also delete the paragraph mark (whole-paragraph deletion)


@dataclass
class NewPara:
    after_para: int
    text: str
    comment: str = ""
    finding_id: str = ""


@dataclass
class CommentOnly:
    para: int
    start: int
    end: int
    comment: str
    finding_id: str = ""


@dataclass
class ApplyReport:
    applied: list[str] = field(default_factory=list)
    refused: list[tuple[str, str]] = field(default_factory=list)


class DocxDoc:
    def __init__(self, data: bytes):
        self.original = data
        self.zin = zipfile.ZipFile(io.BytesIO(data))
        self.parts = {n: self.zin.read(n) for n in self.zin.namelist()}
        self.doc = etree.fromstring(self.parts["word/document.xml"])
        self.body = self.doc.find(W + "body")
        self.paras = [p for p in self.body.iter(W + "p")]
        self._next_id = self._max_id() + 1000
        self.comments_root = None
        if "word/comments.xml" in self.parts:
            self.comments_root = etree.fromstring(self.parts["word/comments.xml"])
        self.date = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def _max_id(self) -> int:
        mx = 0
        for xml_name in ("word/document.xml", "word/comments.xml", "word/footnotes.xml", "word/endnotes.xml"):
            if xml_name in self.parts:
                for m in re.finditer(rb'w:id="(-?\d+)"', self.parts[xml_name]):
                    mx = max(mx, int(m.group(1)))
        return mx

    def nid(self) -> str:
        self._next_id += 1
        return str(self._next_id)

    # ------------------------------------------------------------ text model
    @staticmethod
    def para_text(p) -> str:
        out = []
        for el in p.iter(W + "t", W + "tab", W + "delText"):
            if el.tag == W + "t":
                out.append(el.text or "")
            elif el.tag == W + "tab":
                if el.getparent().tag == W + "r":
                    out.append("\t")
        return "".join(out)

    def texts(self) -> list[str]:
        return [self.para_text(p) for p in self.paras]

    def _atomize(self, p):
        """Split every direct-child run into runs holding exactly one content child."""
        for r in list(p.findall(W + "r")):
            content = [c for c in r if c.tag != W + "rPr"]
            if len(content) <= 1:
                continue
            rpr = r.find(W + "rPr")
            idx = p.index(r)
            new_runs = []
            for c in content:
                nr = etree.Element(W + "r")
                if rpr is not None:
                    nr.append(copy.deepcopy(rpr))
                nr.append(c)
                new_runs.append(nr)
            p.remove(r)
            for k, nr in enumerate(new_runs):
                p.insert(idx + k, nr)

    def _charmap(self, p):
        """Return list of (start, end, element, editable) segments covering para text."""
        segs = []
        pos = 0
        for el in p.iter(W + "t", W + "tab"):
            if el.tag == W + "tab" and el.getparent().tag != W + "r":
                continue
            txt = (el.text or "") if el.tag == W + "t" else "\t"
            run = el.getparent()
            editable = run.tag == W + "r" and run.getparent() is p
            segs.append([pos, pos + len(txt), el, editable])
            pos += len(txt)
        return segs

    def _split_at(self, p, offset: int) -> bool:
        """Ensure a run boundary exists at `offset`. Returns False if inside locked text."""
        for s, e, el, editable in self._charmap(p):
            if s < offset < e:
                if not editable or el.tag != W + "t":
                    return False
                run = el.getparent()
                k = offset - s
                left, right = (el.text or "")[:k], (el.text or "")[k:]
                el.text = left
                el.set(XML_SPACE, "preserve")
                nr = copy.deepcopy(run)
                nt = nr.find(W + "t")
                nt.text = right
                nt.set(XML_SPACE, "preserve")
                run.addnext(nr)
                return True
        return True

    def _runs_in(self, p, start, end):
        out = []
        for s, e, el, editable in self._charmap(p):
            if s >= start and e <= end and e > s:
                out.append((el.getparent(), editable))
        return out

    # ------------------------------------------------------------ primitives
    def _ins_run(self, text: str, rpr):
        ins = etree.Element(W + "ins", {W + "id": self.nid(), W + "author": self.author, W + "date": self.date})
        r = etree.SubElement(ins, W + "r")
        if rpr is not None:
            rp = copy.deepcopy(rpr)
            for bad in rp.findall(W + "ins") + rp.findall(W + "del") + rp.findall(W + "rPrChange"):
                rp.remove(bad)
            r.append(rp)
        t = etree.SubElement(r, W + "t")
        t.text = text
        t.set(XML_SPACE, "preserve")
        return ins

    def _comment(self, text: str) -> str:
        if self.comments_root is None:
            self.comments_root = etree.Element(W + "comments", nsmap={"w": W_NS})
        cid = self.nid()
        c = etree.SubElement(self.comments_root, W + "comment",
                             {W + "id": cid, W + "author": self.author, W + "date": self.date, W + "initials": self.initials})
        for k, line in enumerate(text.split("\n")):
            cp = etree.SubElement(c, W + "p")
            if k == 0:
                ar = etree.SubElement(cp, W + "r")
                etree.SubElement(ar, W + "annotationRef")
            r = etree.SubElement(cp, W + "r")
            t = etree.SubElement(r, W + "t")
            t.text = line
            t.set(XML_SPACE, "preserve")
        return cid

    @staticmethod
    def _ref_run(cid):
        r = etree.Element(W + "r")
        rpr = etree.SubElement(r, W + "rPr")
        etree.SubElement(rpr, W + "vertAlign", {W + "val": "baseline"})
        etree.SubElement(r, W + "commentReference", {W + "id": cid})
        return r

    # ------------------------------------------------------------ apply
    def apply(self, edits: list[Edit], new_paras: list[NewPara], comments: list[CommentOnly],
              author: str, initials: str = "SYA") -> ApplyReport:
        self.author, self.initials = author, initials
        rep = ApplyReport()
        by_para: dict[int, list] = {}
        for e in edits:
            by_para.setdefault(e.para, []).append(e)
        for c in comments:
            by_para.setdefault(c.para, []).append(c)
        for pi, items in by_para.items():
            p = self.paras[pi]
            self._atomize(p)
            # right-to-left so earlier offsets stay valid
            items.sort(key=lambda x: x.start, reverse=True)
            last_start = None
            for it in items:
                if last_start is not None and it.end > last_start:
                    rep.refused.append((it.finding_id, "overlaps another edit"))
                    continue
                ok = self._apply_one(p, it)
                if ok is True:
                    rep.applied.append(it.finding_id)
                    last_start = it.start
                else:
                    rep.refused.append((it.finding_id, ok))
        # paragraphs inserted last; process highest anchor first so indices stay valid
        for npara in sorted(new_paras, key=lambda x: x.after_para, reverse=True):
            self._insert_para(npara)
            rep.applied.append(npara.finding_id)
        return rep

    def _apply_one(self, p, it):
        start, end = it.start, it.end
        if not (self._split_at(p, start) and self._split_at(p, end)):
            return "edit falls inside locked text (existing revision / field / hyperlink)"
        runs = self._runs_in(p, start, end)
        if any(not ed for _r, ed in runs):
            return "edit spans locked text"
        if isinstance(it, CommentOnly):
            if not runs:
                return "nothing to anchor comment"
            cid = self._comment(it.comment)
            runs[0][0].addprevious(etree.Element(W + "commentRangeStart", {W + "id": cid}))
            last = runs[-1][0]
            cre = etree.Element(W + "commentRangeEnd", {W + "id": cid})
            last.addnext(cre)
            cre.addnext(self._ref_run(cid))
            return True
        # locate insertion anchor (run before start) for formatting when pure insertion
        rpr = None
        anchor_run = None
        if runs:
            rpr = runs[0][0].find(W + "rPr")
        else:
            for s, e, el, editable in self._charmap(p):
                if e == start and el.getparent().getparent() is p:
                    anchor_run = el.getparent(); rpr = anchor_run.find(W + "rPr")
            if anchor_run is None:
                for s, e, el, editable in self._charmap(p):
                    if s == start and el.getparent().getparent() is p:
                        rpr = el.getparent().find(W + "rPr")
                        anchor_run = el.getparent()
                        break
        first_node = last_node = None
        if runs:
            dl = etree.Element(W + "del", {W + "id": self.nid(), W + "author": self.author, W + "date": self.date})
            runs[0][0].addprevious(dl)
            for r, _ in runs:
                for t in r.findall(W + "t"):
                    t.tag = W + "delText"
                    t.set(XML_SPACE, "preserve")
                dl.append(r)
            first_node = last_node = dl
        if it.new:
            ins = self._ins_run(it.new, rpr)
            if last_node is not None:
                last_node.addnext(ins)
            elif anchor_run is not None and anchor_run is not None:
                # pure insertion: after the run that ends at start, else before the run that starts at start
                ends_here = any(e == start and el.getparent() is anchor_run for s, e, el, _ in self._charmap(p))
                (anchor_run.addnext if ends_here else anchor_run.addprevious)(ins)
            else:
                p.append(ins)
            first_node = first_node if first_node is not None else ins
            last_node = ins
        if getattr(it, "delete_mark", False):
            ppr = p.find(W + "pPr")
            if ppr is None:
                ppr = etree.Element(W + "pPr"); p.insert(0, ppr)
            rpr_m = ppr.find(W + "rPr")
            if rpr_m is None:
                rpr_m = etree.Element(W + "rPr")
                tail = ppr.find(W + "sectPr")
                if tail is None:
                    tail = ppr.find(W + "pPrChange")
                (tail.addprevious if tail is not None else ppr.append)(rpr_m)
            rpr_m.insert(0, etree.Element(W + "del", {W + "id": self.nid(), W + "author": self.author, W + "date": self.date}))
        if it.comment and first_node is not None:
            cid = self._comment(it.comment)
            first_node.addprevious(etree.Element(W + "commentRangeStart", {W + "id": cid}))
            cre = etree.Element(W + "commentRangeEnd", {W + "id": cid})
            last_node.addnext(cre)
            cre.addnext(self._ref_run(cid))
        return True

    def _insert_para(self, npara: NewPara):
        anchor = self.paras[npara.after_para]
        newp = etree.Element(W + "p")
        ppr_src = anchor.find(W + "pPr")
        ppr = copy.deepcopy(ppr_src) if ppr_src is not None else etree.Element(W + "pPr")
        for bad in ppr.findall(W + "pPrChange") + ppr.findall(W + "sectPr"):
            ppr.remove(bad)
        rpr_mark = ppr.find(W + "rPr")
        if rpr_mark is None:
            rpr_mark = etree.SubElement(ppr, W + "rPr")
        for bad in list(rpr_mark):
            if bad.tag in (W + "ins", W + "del"):
                rpr_mark.remove(bad)
        rpr_mark.insert(0, etree.Element(W + "ins", {W + "id": self.nid(), W + "author": self.author, W + "date": self.date}))
        newp.append(ppr)
        first_run = anchor.find(W + "r")
        rpr = first_run.find(W + "rPr") if first_run is not None else None
        rpr = copy.deepcopy(rpr) if rpr is not None else None
        if rpr is not None:
            for tag in ("b", "bCs", "u", "caps", "highlight"):
                for el in rpr.findall(W + tag):
                    rpr.remove(el)
        ins = self._ins_run(npara.text, rpr)
        if npara.comment:
            cid = self._comment(npara.comment)
            newp.append(etree.Element(W + "commentRangeStart", {W + "id": cid}))
            newp.append(ins)
            newp.append(etree.Element(W + "commentRangeEnd", {W + "id": cid}))
            newp.append(self._ref_run(cid))
        else:
            newp.append(ins)
        anchor.addnext(newp)

    # ------------------------------------------------------------ save
    def save(self) -> bytes:
        parts = dict(self.parts)
        parts["word/document.xml"] = etree.tostring(self.doc, xml_declaration=True, encoding="UTF-8", standalone=True)
        if self.comments_root is not None:
            parts["word/comments.xml"] = etree.tostring(self.comments_root, xml_declaration=True, encoding="UTF-8", standalone=True)
            parts = _ensure_comments_part(parts)
        return _zip(parts, self.zin)


def _ensure_comments_part(parts: dict) -> dict:
    rels = etree.fromstring(parts["word/_rels/document.xml.rels"])
    if not any(r.get("Type") == COMMENTS_REL for r in rels):
        ids = {r.get("Id") for r in rels}
        k = 1
        while f"rIdC{k}" in ids:
            k += 1
        etree.SubElement(rels, "{%s}Relationship" % REL_NS, {"Id": f"rIdC{k}", "Type": COMMENTS_REL, "Target": "comments.xml"})
        parts["word/_rels/document.xml.rels"] = etree.tostring(rels, xml_declaration=True, encoding="UTF-8", standalone=True)
    ct = etree.fromstring(parts["[Content_Types].xml"])
    if not any(o.get("PartName") == "/word/comments.xml" for o in ct):
        etree.SubElement(ct, "{%s}Override" % CT_NS, {"PartName": "/word/comments.xml", "ContentType": COMMENTS_CT})
        parts["[Content_Types].xml"] = etree.tostring(ct, xml_declaration=True, encoding="UTF-8", standalone=True)
    return parts


def _zip(parts: dict, zin: zipfile.ZipFile | None) -> bytes:
    bio = io.BytesIO()
    order = [i.filename for i in zin.infolist()] if zin else list(parts)
    order = ["[Content_Types].xml"] + [n for n in order if n != "[Content_Types].xml"] + [n for n in parts if n not in order]
    with zipfile.ZipFile(bio, "w", zipfile.ZIP_DEFLATED) as z:
        for n in order:
            if n in parts and not n.endswith("/"):
                z.writestr(n, parts[n])
    return bio.getvalue()


# ------------------------------------------------------------------ accept all (clean copy)
def accept_all(data: bytes, strip_comments: bool = True) -> bytes:
    zin = zipfile.ZipFile(io.BytesIO(data))
    parts = {n: zin.read(n) for n in zin.namelist()}
    for name in [n for n in parts if re.match(r"word/(document|header\d*|footer\d*|footnotes|endnotes)\.xml$", n)]:
        root = etree.fromstring(parts[name])
        # remove deletions
        for el in list(root.iter(W + "del", W + "moveFrom")):
            par = el.getparent()
            if par is None:
                continue
            if par.tag == W + "rPr":
                # deleted paragraph mark: merge paragraph with following one
                p = par.getparent().getparent() if par.getparent().tag == W + "pPr" else None
                par.remove(el)
                if p is not None and p.tag == W + "p":
                    p.set("__merge", "1")
                continue
            par.remove(el)
        # unwrap insertions
        for el in list(root.iter(W + "ins", W + "moveTo")):
            par = el.getparent()
            if par is None:
                continue
            if par.tag == W + "rPr":
                par.remove(el)
                continue
            idx = par.index(el)
            for k, ch in enumerate(list(el)):
                par.insert(idx + k, ch)
            par.remove(el)
        for tag in ("rPrChange", "pPrChange", "sectPrChange", "tblPrChange", "trPrChange", "tcPrChange", "numberingChange"):
            for el in list(root.iter(W + tag)):
                el.getparent().remove(el)
        for p in list(root.iter(W + "p")):
            if p.get("__merge"):
                del p.attrib["__merge"]
                nxt = p.getnext()
                if nxt is not None and nxt.tag == W + "p":
                    for ch in [c for c in p if c.tag != W + "pPr"]:
                        nxt_ppr = nxt.find(W + "pPr")
                        (nxt_ppr.addnext if nxt_ppr is not None else (lambda x: nxt.insert(0, x)))(ch)
                    p.getparent().remove(p)
                elif not DocxDoc.para_text(p).strip():
                    p.getparent().remove(p)
        if strip_comments:
            for tag in ("commentRangeStart", "commentRangeEnd"):
                for el in list(root.iter(W + tag)):
                    el.getparent().remove(el)
            for el in list(root.iter(W + "commentReference")):
                r = el.getparent()
                r.getparent().remove(r)
        parts[name] = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
    if strip_comments:
        for n in ["word/comments.xml", "word/commentsExtended.xml", "word/commentsIds.xml", "word/commentsExtensible.xml", "word/people.xml"]:
            parts.pop(n, None)
        rels = etree.fromstring(parts["word/_rels/document.xml.rels"])
        for r in list(rels):
            if "comments" in (r.get("Type") or "").lower() or r.get("Target", "").startswith("comments") or "people" in (r.get("Type") or ""):
                rels.remove(r)
        parts["word/_rels/document.xml.rels"] = etree.tostring(rels, xml_declaration=True, encoding="UTF-8", standalone=True)
        ct = etree.fromstring(parts["[Content_Types].xml"])
        for o in list(ct):
            pn = o.get("PartName") or ""
            if pn.startswith("/word/comments") or pn == "/word/people.xml":
                ct.remove(o)
        parts["[Content_Types].xml"] = etree.tostring(ct, xml_declaration=True, encoding="UTF-8", standalone=True)
    return _zip(parts, zin)


def accepted_text(data: bytes) -> list[str]:
    d = DocxDoc(accept_all(data))
    return d.texts()


def tracked_stats(data: bytes) -> dict:
    z = zipfile.ZipFile(io.BytesIO(data))
    x = z.read("word/document.xml")
    c = z.read("word/comments.xml") if "word/comments.xml" in z.namelist() else b""
    return {"insertions": len(re.findall(rb"<w:ins ", x)), "deletions": len(re.findall(rb"<w:del ", x)),
            "comments": len(re.findall(rb"<w:comment ", c))}
