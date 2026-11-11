"""Formatting helpers for Indian legal drafting (amounts in words, ordinal dates, etc.)."""
from __future__ import annotations

import datetime as dt
import re

_ONES = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten", "Eleven",
         "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen"]
_TENS = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]


def _two(n: int) -> str:
    if n < 20:
        return _ONES[n]
    t, o = divmod(n, 10)
    return _TENS[t] + ("-" + _ONES[o] if o else "")


def _three(n: int) -> str:
    h, r = divmod(n, 100)
    parts = []
    if h:
        parts.append(_ONES[h] + " Hundred")
    if r:
        parts.append(_two(r))
    return " ".join(parts)


def words_indian(n: int) -> str:
    """Integer to words in the Indian numbering system (lakh / crore)."""
    if n == 0:
        return "Zero"
    if n < 0:
        return "Minus " + words_indian(-n)
    crore, n = divmod(n, 10_000_000)
    lakh, n = divmod(n, 100_000)
    thousand, n = divmod(n, 1000)
    parts = []
    if crore:
        parts.append(words_indian(crore) + " Crore")
    if lakh:
        parts.append(_two(lakh) + " Lakh")
    if thousand:
        parts.append(_two(thousand) + " Thousand")
    if n:
        parts.append(_three(n))
    return " ".join(parts)


def indian_grouping(n: float) -> str:
    neg = n < 0
    n = abs(n)
    whole = int(round(n))
    s = str(whole)
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        head = re.sub(r"(\d)(?=(\d\d)+$)", r"\1,", head)
        s = head + "," + tail
    return ("-" if neg else "") + s


def money(v) -> str:
    try:
        n = float(str(v).replace(",", "").replace("Rs.", "").replace("₹", "").strip().rstrip("/-"))
    except (TypeError, ValueError):
        return str(v)
    return f"Rs. {indian_grouping(n)}/- (Rupees {words_indian(int(round(n)))} Only)"


def money_short(v) -> str:
    try:
        n = float(str(v).replace(",", ""))
    except (TypeError, ValueError):
        return str(v) if v not in (None, "") else ""
    return f"Rs. {indian_grouping(n)}/-"


def num_words(v) -> str:
    try:
        n = int(float(v))
    except (TypeError, ValueError):
        return str(v)
    return f"{n} ({words_indian(n)})"


def ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suf = "th"
    else:
        suf = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suf}"


_DATE_FORMATS = ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%d %B %Y", "%d %b %Y", "%B %d, %Y"]


def parse_date(v) -> dt.date | None:
    if isinstance(v, dt.date):
        return v
    s = str(v or "").strip()
    s = re.sub(r"(\d+)(st|nd|rd|th)\b", r"\1", s).replace(",", " ")
    s = re.sub(r"\s+", " ", s).strip()
    for f in _DATE_FORMATS:
        try:
            return dt.datetime.strptime(s, f.replace(",", "")).date()
        except ValueError:
            continue
    return None


def legal_date(v) -> str:
    d = parse_date(v)
    if not d:
        return str(v)
    return f"{ordinal(d.day)} {d.strftime('%B')}, {d.year}"


def norm_name(s: str) -> str:
    s = re.sub(r"\b(late|shri|smt|mr|mrs|ms|dr|kum)\.?\s+", "", (s or "").lower())
    return re.sub(r"[^a-z]", "", s)


def to_float(v) -> float | None:
    if v in (None, ""):
        return None
    try:
        return float(str(v).replace(",", "").replace("Rs.", "").replace("₹", "").strip().rstrip("/-"))
    except ValueError:
        return None
