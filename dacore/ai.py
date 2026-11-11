"""Optional Claude integration (structured outputs).

Claude is used as an *assistant* to the deterministic engines, never as the source of truth:
* extracted facts must quote a snippet that is verified to exist in the source text;
* review suggestions must quote text that exists verbatim in the paragraph, and then pass the
  same reasonableness test as rule-based amendments;
* research answers are always marked "advocate verification required" and may cite only
  sources the model is given or can quote – the prompt forbids inventing authorities.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from . import schema
from .config import AI_ENABLED, CLAUDE_MODEL


def available() -> bool:
    if AI_ENABLED == "off":
        return False
    if AI_ENABLED == "on":
        return True
    return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")
                or (Path.home() / ".config" / "anthropic").exists())


def _client():
    import anthropic
    return anthropic.Anthropic()


def _json_call(system: str, user: str, schema_obj: dict, max_tokens: int = 16000) -> dict:
    """Structured-output call with server-side refusal fallback; falls back to a plain call if the SDK lacks the beta."""
    import anthropic
    client = _client()
    kwargs = dict(model=CLAUDE_MODEL, max_tokens=max_tokens, system=system,
                  messages=[{"role": "user", "content": user}],
                  output_config={"effort": "high", "format": {"type": "json_schema", "schema": schema_obj}})
    try:
        resp = client.beta.messages.create(betas=["server-side-fallback-2026-07-01"], fallbacks="default", **kwargs)
    except (TypeError, anthropic.BadRequestError):
        resp = client.messages.create(**kwargs)
    if resp.stop_reason == "refusal":
        raise RuntimeError("Claude declined this request")
    text = next(b.text for b in resp.content if b.type == "text")
    return json.loads(text)


SYSTEM_LEGAL = ("You assist a Maharashtra advocate who represents co-operative housing societies in redevelopment. "
                "Work only from the text supplied. Never invent facts, figures, dates, judgments, sections or circulars. "
                "If something is uncertain, say so. Society-protective but commercially reasonable.")


def extract_facts(text: str, doc_type: str) -> list[dict]:
    keys = [f.key for f in schema.FIELDS]
    sch = {"type": "object", "additionalProperties": False, "required": ["facts"],
           "properties": {"facts": {"type": "array", "items": {"type": "object", "additionalProperties": False,
                                                                 "required": ["field", "value", "quote"],
                                                                 "properties": {"field": {"type": "string", "enum": keys},
                                                                                "value": {"type": "string"},
                                                                                "quote": {"type": "string"}}}}}}
    prompt = (f"Document type: {doc_type}.\nExtract every fact that matches one of the field keys. For each, give the value and an exact quote "
              f"(copied verbatim, 5-40 words) from the document that states it. Omit anything not stated.\n\n<document>\n{text[:180000]}\n</document>")
    out = _json_call(SYSTEM_LEGAL, prompt, sch)
    facts = []
    for f in out.get("facts", []):
        if f["quote"] and f["quote"][:60] in text:
            facts.append(f)
    return facts


def review_suggestions(paragraphs: list[str], limit_chars: int = 150000) -> list[dict]:
    numbered, total = [], 0
    for i, p in enumerate(paragraphs):
        if p.strip():
            line = f"[{i}] {p}"
            total += len(line)
            if total > limit_chars:
                break
            numbered.append(line)
    sch = {"type": "object", "additionalProperties": False, "required": ["suggestions"],
           "properties": {"suggestions": {"type": "array", "items": {"type": "object", "additionalProperties": False,
               "required": ["para", "find", "replace", "title", "category", "severity", "reason", "benefit", "risk", "mandatory"],
               "properties": {"para": {"type": "integer"}, "find": {"type": "string"}, "replace": {"type": "string"},
                              "title": {"type": "string"}, "category": {"type": "string", "enum": ["Legal", "Commercial", "Construction", "Society Protection"]},
                              "severity": {"type": "string", "enum": ["Critical", "High", "Medium", "Low"]},
                              "reason": {"type": "string"}, "benefit": {"type": "string"}, "risk": {"type": "string"}, "mandatory": {"type": "boolean"}}}}}}
    prompt = ("Review this Development Agreement from the Society's perspective. Propose only targeted amendments to clauses that are "
              "actually deficient. For each, `find` must be an exact substring of the numbered paragraph and `replace` the minimal new wording "
              "in the same drafting style. Do not introduce new figures or facts (use [●]); do not delete provisions that already protect the Society; "
              "do not rewrite satisfactory clauses. At most 25 suggestions.\n\n" + "\n".join(numbered))
    out = _json_call(SYSTEM_LEGAL, prompt, sch)
    return [dict(s, id=f"AI-{k + 1:02d}") for k, s in enumerate(out.get("suggestions", []))]


def legal_research(question: str, register: list[dict]) -> dict:
    sch = {"type": "object", "additionalProperties": False, "required": ["answer", "sources_used", "uncertain_points"],
           "properties": {"answer": {"type": "string"}, "sources_used": {"type": "array", "items": {"type": "string"}},
                          "uncertain_points": {"type": "array", "items": {"type": "string"}}}}
    reg = "\n".join(f"- [{r['code']}] {r['title']} – {r['provision']}: {r['proposition']} (status: {r['verification_status']})" for r in register)
    prompt = (f"Question: {question}\n\nAnswer using ONLY the register entries below. Cite entries by their [code]. If the register does not answer the "
              f"question, say so and list what must be researched. Never cite any judgment, section or circular not in the register.\n\n{reg}")
    out = _json_call(SYSTEM_LEGAL, prompt, sch, max_tokens=8000)
    out["verification"] = "Advocate verification required before reliance."
    return out
