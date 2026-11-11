"""DA reviewer: analyse a third-party Development Agreement from the Society's perspective."""
from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass, field

from .redline import CommentOnly, DocxDoc, Edit, NewPara, accept_all, accepted_text, tracked_stats
from .rules import MISSING, RULES, RR, detect_terms

NUM_PREFIX = re.compile(r"^\s*(?:\(?\d+(?:\.\d+)*\)?\.?|\(?[a-z]{1,2}\)|\(?[ivxl]+\)|[A-Z]\.|\d+\.\d+\.?)(?:\s+|\t)")
BENEFICIAL = [r"Society shall be entitled", r"free of cost", r"at (?:its|the) (?:own )?cost(?:s)? and expense", r"without prejudice to the (?:rights|right) of the Society",
              r"Developer shall (?:pay|indemnify|bear)", r"Developer hereby indemnifies", r"shall continue to apply irrespective", r"shall not (?:be entitled to )?mortgage",
              r"excluding Existing Member", r"prior (?:written )?consent of the Society"]
SEVERITY_ORDER = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}


@dataclass
class Finding:
    id: str
    rule: str
    title: str
    category: str
    severity: str
    mandatory: bool
    kind: str                 # amendment | insertion | comment
    para: int
    clause_ref: str
    original: str
    proposed: str
    reason: str
    benefit: str
    risk: str
    legal: str = ""
    negotiable: bool = False
    status: str = "proposed"  # proposed | applied | refused
    note: str = ""
    source: str = "rules"     # rules | ai


def _clause_refs(texts: list[str]) -> list[str]:
    refs, art, count = [], "Preamble", 0
    for t in texts:
        s = t.strip()
        m = re.match(r"^ARTICLE\s*[-–—]?\s*([IVXLC]+|\d+)", s, re.I)
        if m:
            art, count = f"Article {m.group(1)}", 0
            refs.append(art); continue
        if re.match(r"^(FIRST|SECOND|THIRD|FOURTH|FIFTH|SIXTH|SEVENTH|EIGHTH|NINTH|TENTH|ELEVENTH|TWELFTH|TWELTH)\s+SCHEDULE|^SCHEDULE\s+[IVX\d]+", s, re.I):
            art, count = s[:30].title(), 0
        if s:
            count += 1
        nm = NUM_PREFIX.match(t)
        refs.append(f"{art}, cl. {nm.group(0).strip()}" if nm else f"{art}, para {count}")
    return refs


def _sentence_bounds(text: str, s: int, e: int) -> tuple[int, int]:
    a = max(text.rfind(". ", 0, s) + 2, 0) if text.rfind(". ", 0, s) >= 0 else 0
    b = text.find(". ", e)
    b = len(text) if b < 0 else b + 1
    return a, b


def reasonable(rule_like, original_para: str, start: int, end: int, new: str) -> str | None:
    """Return None if the amendment passes the reasonableness test, else the reason it is refused."""
    deleted = original_para[start:end]
    if not getattr(rule_like, "allow_beneficial_delete", False):
        for pat in BENEFICIAL:
            if re.search(pat, deleted, re.I):
                return f"would delete a beneficial provision (“{re.search(pat, deleted, re.I).group(0)}”)"
    if new and not getattr(rule_like, "allows_figures", False):
        figs_new = set(re.findall(r"\d[\d,]*(?:\.\d+)?", new)) - {"9", "1996", "14", "3", "18", "79", "73", "74", "2016", "1872", "11", "19", "10"}
        figs_orig = set(re.findall(r"\d[\d,]*(?:\.\d+)?", original_para))
        extra = figs_new - figs_orig
        if extra:
            return "introduces new figures (" + ", ".join(sorted(extra)) + ") – use [●] and mark negotiable"
    return None


@dataclass
class ReviewResult:
    findings: list[Finding] = field(default_factory=list)
    redline: bytes = b""
    clean: bytes = b""
    stats: dict = field(default_factory=dict)
    checklist: list[dict] = field(default_factory=list)
    terms: dict = field(default_factory=dict)
    texts: list[str] = field(default_factory=list)
    original_sha256: str = ""


def review_docx(data: bytes, author: str, extra_suggestions: list[dict] | None = None) -> ReviewResult:
    res = ReviewResult(original_sha256=hashlib.sha256(data).hexdigest())
    doc = DocxDoc(data)
    texts = doc.texts()
    res.texts = texts
    full = "\n".join(texts)
    terms = detect_terms(full)
    res.terms = terms
    refs = _clause_refs(texts)
    from .redline import W
    in_table = [any(a.tag == W + "tc" for a in p.iterancestors()) for p in doc.paras]
    body_end = next((i for i, t in enumerate(texts) if re.match(
        r"^\s*(?:FIRST\s+SCHEDULE|SCHEDULE\s*[-–]?\s*(?:I|1)\b|IN WITNESS WHERE)", t.strip(), re.I)), len(texts))
    edits, newp, comms = [], [], []
    fid = 0
    used_spans: dict[int, list[tuple[int, int]]] = {}

    def add_finding(rule, kind, pi, original, proposed, note="", negotiable=False, source="rules"):
        nonlocal fid
        fid += 1
        f = Finding(f"F{fid:03d}", rule.id, rule.title, rule.category, rule.severity, rule.mandatory, kind, pi, refs[pi] if pi < len(refs) else "",
                    original, proposed, rule.reason, rule.benefit, rule.risk, rule.legal, negotiable or not rule.mandatory, note=note, source=source)
        res.findings.append(f)
        return f

    def span_free(pi, s, e):
        for a, b in used_spans.get(pi, []):
            if s < b and a < e or (s == e and a <= s <= b):
                return False
        used_spans.setdefault(pi, []).append((s, e))
        return True

    for rule in RULES:
        rx = re.compile(rule.pattern, re.I | re.M)
        for pi, t in enumerate(texts):
            if not t.strip():
                continue
            m = rx.search(t)
            if not m:
                continue
            if rule.requires and not re.search(rule.requires, t, re.I):
                continue
            if rule.guard and re.search(rule.guard, t, re.I):
                continue
            s, e = (m.start("x"), m.end("x")) if "x" in rx.groupindex else (m.start(), m.end())
            if rule.action == "replace":
                new = rule.text
            elif rule.action == "delete":
                new = ""
            elif rule.action == "insert_after":
                s = e; new = rule.text
            elif rule.action == "append":
                body = t.rstrip()
                s = e = len(body) - 1 if body.endswith(".") else len(body)
                new = rule.text
            elif rule.action in ("replace_para", "delete_para"):
                nm = NUM_PREFIX.match(t)
                s, e = (nm.end() if nm else len(t) - len(t.lstrip())), len(t.rstrip())
                new = rule.text if rule.action == "replace_para" else ""
            else:  # comment
                new = None
            a, b = _sentence_bounds(t, s, e)
            original = t[a:b].strip() if rule.action not in ("replace_para", "delete_para") else t.strip()
            if rule.action == "comment":
                if not span_free(pi, m.start(), m.end()):
                    continue
                f = add_finding(rule, "comment", pi, original, "(no textual change – negotiation point)", negotiable=True)
                comms.append(CommentOnly(pi, m.start(), m.end(), _comment_text(f), f.id))
                continue
            why = reasonable(rule, t, s, e, new)
            proposed = (t[a:s] + (new or "") + t[e:b]).strip() if rule.action not in ("replace_para", "delete_para") else (new or "[clause deleted]")
            if why:
                f = add_finding(rule, "amendment", pi, original, proposed, note=f"Not applied automatically: {why}.")
                f.status = "refused"
                continue
            if not span_free(pi, s, e):
                continue
            f = add_finding(rule, "amendment", pi, original, proposed, negotiable=rule.allows_figures)
            edits.append(Edit(pi, s, e, new or "", _comment_text(f), f.id, delete_mark=(rule.action == "delete_para")))

    # missing clauses
    for mc in MISSING:
        if re.search(mc.present, full, re.I):
            continue
        anchor = _find_anchor(mc.anchor, texts, in_table, body_end)
        if anchor is None:
            cands = [i for i in range(body_end) if texts[i].strip() and not in_table[i]]
            anchor = cands[-1] if cands else len(texts) - 1
        text = mc.text.format(**terms)
        nm = NUM_PREFIX.match(texts[anchor])
        prefix = ""
        if nm and re.match(r"^\s*\d+(?:\.\d+)+", nm.group(0)):
            prefix = nm.group(0).strip().rstrip(".") + "A\t"
        rr = RR(mc.id, mc.title, "Missing Clause", mc.severity, "", "insert", reason=mc.reason, benefit=mc.benefit, risk=mc.risk, legal=mc.legal, mandatory=mc.mandatory)
        f = add_finding(rr, "insertion", anchor, "(no corresponding provision in the draft)", prefix.replace("\t", " ") + text, negotiable="[●]" in text)
        newp.append(NewPara(anchor, prefix + text, _comment_text(f), f.id))

    # AI suggestions (already validated to reference exact text)
    for sug in extra_suggestions or []:
        pi = sug.get("para")
        if pi is None or pi >= len(texts):
            continue
        t = texts[pi]
        k = t.find(sug.get("find", "\0"))
        if k < 0 or not sug.get("find"):
            continue
        rr = RR(sug.get("id", "AI"), sug.get("title", "AI-suggested amendment"), sug.get("category", "Legal"), sug.get("severity", "Medium"), "", "replace",
                reason=sug.get("reason", ""), benefit=sug.get("benefit", ""), risk=sug.get("risk", ""), mandatory=bool(sug.get("mandatory")))
        new = sug.get("replace", "")
        why = reasonable(rr, t, k, k + len(sug["find"]), new)
        a, b = _sentence_bounds(t, k, k + len(sug["find"]))
        f = add_finding(rr, "amendment", pi, t[a:b].strip(), (t[a:k] + new + t[k + len(sug['find']):b]).strip(), source="ai",
                        note=("Not applied: " + why) if why else "Suggested by Claude; verify before accepting.")
        if why or not span_free(pi, k, k + len(sug["find"])):
            f.status = "refused"
            continue
        edits.append(Edit(pi, k, k + len(sug["find"]), new, _comment_text(f), f.id))

    rep = doc.apply(edits, newp, comms, author=author)
    applied = set(rep.applied)
    refused = dict(rep.refused)
    for f in res.findings:
        if f.status == "refused":
            continue
        if f.id in applied:
            f.status = "applied"
        elif f.id in refused:
            f.status = "refused"; f.note = "Not applied automatically: " + refused[f.id]
    res.redline = doc.save()
    res.clean = accept_all(res.redline)
    res.stats = tracked_stats(res.redline)
    res.checklist = execution_checklist(texts)
    res.findings.sort(key=lambda f: (SEVERITY_ORDER.get(f.severity, 9), f.para))
    return res


ART_HEAD = re.compile(r"^\s*ARTICLE\s*[-–—]?\s*(?:[IVXLC]+|\d+)\b", re.I)


def _find_anchor(spec: str, texts: list[str], in_table: list[bool], body_end: int) -> int | None:
    """Insert position for a missing clause: the last body paragraph of the Article whose title matches."""
    if spec.startswith("article:"):
        rx = re.compile(spec[8:], re.I)
        heads = [i for i in range(body_end) if ART_HEAD.match(texts[i])]
        for k, h in enumerate(heads):
            title = texts[h] + " " + " ".join(texts[h + 1:h + 3])
            if rx.search(title):
                end = heads[k + 1] if k + 1 < len(heads) else body_end
                cands = [i for i in range(h + 1, end) if texts[i].strip() and not in_table[i] and len(texts[i]) > 40]
                if cands:
                    return cands[-1]
        return None
    last = None
    for i in range(body_end):
        if not in_table[i] and len(texts[i]) > 40 and re.search(spec, texts[i], re.I):
            last = i
    return last


def _comment_text(f: Finding) -> str:
    parts = [f"[{f.severity} | {f.category} | {'Mandatory' if f.mandatory and not f.negotiable else 'Negotiable'}] {f.title}", f.reason]
    if f.benefit:
        parts.append("Society's benefit: " + f.benefit)
    if f.legal:
        parts.append("Reference: " + f.legal + " (advocate to verify current position).")
    return "\n".join(p for p in parts if p)


def execution_checklist(texts: list[str]) -> list[dict]:
    full = "\n".join(texts)
    items = []
    blanks = [(i, t) for i, t in enumerate(texts) if re.search(r"_{3,}|\[\s*●\s*\]|\.{5,}", t)]
    for i, t in blanks:
        items.append({"type": "Blank / unfilled field", "where": f"para {i + 1}", "detail": re.sub(r"\s+", " ", t)[:160]})
    for m in re.finditer(r"(Annexure|Exhibit|Schedule|Clause|Article)\s*[-–]?\s*_{2,}", full, re.I):
        items.append({"type": "Unnumbered reference", "where": m.group(0), "detail": full[max(0, m.start() - 80): m.end() + 40].replace("\n", " ")})
    referenced = set(re.findall(r"(FIRST|SECOND|THIRD|FOURTH|FIFTH|SIXTH|SEVENTH|EIGHTH|NINTH|TENTH|ELEVENTH|TWELFTH|TWELTH)\s+SCHEDULE", full, re.I))
    for sch in referenced:
        heads = [t for t in texts if re.match(rf"^\s*{sch}\s+SCHEDULE\s*$", t.strip(), re.I)]
        if not heads:
            items.append({"type": "Schedule referred to but not found", "where": sch.title() + " Schedule", "detail": "Referred in the body but no schedule heading found."})
    ann_refs = set(x.upper() for x in re.findall(r"Annexure\s*[‘'“\"]?\s*([A-Z0-9]{1,2})\b", full))
    ann_heads = set(x.upper() for t in texts for x in re.findall(r"^\s*ANNEXURE\s*[-–]?\s*[‘'“\"]?([A-Z0-9]{1,2})", t.strip(), re.I))
    for a in sorted(ann_refs - ann_heads):
        items.append({"type": "Annexure referred to but not attached / listed", "where": f"Annexure {a}", "detail": "Ensure the document is annexed before execution."})
    for need, rx in [("Bank guarantee format", r"format of (?:the )?bank guarantee"), ("PAAA format", r"format of (?:the )?(?:permanent alternate accommodation|PAAA)|template of the aforesaid PAAA"),
                     ("Power of attorney draft", r"power of attorney"), ("Member-wise area schedule", r"carpet area"), ("Amenities / specifications annexure", r"amenit"),
                     ("Section 79A order", r"79\s*\(?A\)?"), ("SGBM resolution approving DA", r"(?:SGBM|special general body meeting)"), ("Developer board resolution", r"board resolution")]:
        if not re.search(rx, full, re.I):
            items.append({"type": "Document / annexure not provided for", "where": need, "detail": "Not referred to in the draft – add before execution."})
    return items


def findings_dicts(res: ReviewResult) -> list[dict]:
    return [asdict(f) for f in res.findings]
