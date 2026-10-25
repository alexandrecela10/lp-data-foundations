"""Claude, only when asked for and a key is present. Every caller has an offline path.

Live mode needs both ANTHROPIC_API_KEY and ANSWERDESK_LIVE=1, so a key in the environment never
starts paid calls by itself. The hosted demo never sets ANSWERDESK_LIVE. Keys are never printed.
Model: claude-sonnet-5-5 ($2 / $10 per million input / output tokens).
"""
from __future__ import annotations

import json
import os
import time

MODEL = "claude-sonnet-5-5"
NOTICE = "Questions go to Anthropic. Do not enter real data."


def available() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY")) and os.environ.get("ANSWERDESK_LIVE") == "1"


def ask_json(system: str, user: str, schema: dict, max_tokens: int = 4000) -> tuple[dict, dict]:
    """One structured call. Returns (parsed JSON, usage dict with tokens and seconds)."""
    import anthropic

    client = anthropic.Anthropic()
    t0 = time.perf_counter()
    kwargs = dict(model=MODEL, max_tokens=max_tokens, system=system,
                  messages=[{"role": "user", "content": user}],
                  output_config={"effort": "low", "format": {"type": "json_schema", "schema": schema}})
    try:
        resp = client.beta.messages.create(betas=["server-side-fallback-2026-07-01"], fallbacks="default", **kwargs)
    except (TypeError, anthropic.BadRequestError):
        resp = client.messages.create(**kwargs)
    secs = time.perf_counter() - t0
    usage = dict(input_tokens=resp.usage.input_tokens, output_tokens=resp.usage.output_tokens, seconds=secs)
    if resp.stop_reason == "refusal":
        return {"refused": True, "text": "The model declined."}, usage
    text = next((b.text for b in resp.content if b.type == "text"), "{}")
    return json.loads(text), usage


def strict(schema: dict) -> dict:
    """JSON schema with additionalProperties false at every object level."""
    if schema.get("type") == "object":
        schema["additionalProperties"] = False
        for v in schema.get("properties", {}).values():
            strict(v)
    if schema.get("type") == "array" and isinstance(schema.get("items"), dict):
        strict(schema["items"])
    return schema


ANSWER_SCHEMA = strict({
    "type": "object",
    "properties": {
        "text": {"type": "string"},
        "value": {"type": ["number", "null"]},
        "items": {"type": "array", "items": {"type": "string"}},
        "date": {"type": ["string", "null"]},
        "table": {"type": "array", "items": {"type": "object", "properties": {
            "name": {"type": "string"}, "value": {"type": "number"}}, "required": ["name", "value"]}},
        "refused": {"type": "boolean"},
        "citations": {"type": "array", "items": {"type": "string"}},
        "routes": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["text", "value", "items", "date", "table", "refused", "citations", "routes"],
})


ANSWER_RULES = ("Answer in JSON. value: the single number asked for (in $m, a multiple, or a rate as a fraction), "
                "else null. items: names or document ids when a list is asked for. date: YYYY-MM-DD when a date is asked "
                "for. table: one row per fund when 'each' fund is asked. routes: for exposure questions, one string per "
                "route as 'direct:<fund name>', 'fof:<underlying fund name>' or 'coinvest:<reference>'. refused: true if "
                "the data can't answer or the question asks for advice or uses a news figure. citations: document ids used.")


def to_answer(ans, data: dict, sourced: bool, defined: bool = False):
    """Fill an Answer from the model's JSON."""
    import datetime as dt
    from .answer import Shown
    ans.text = data.get("text", "")
    ans.value = data.get("value")
    ans.items = list(data.get("items") or [])
    ans.route_sigs = sorted(data.get("routes") or [])
    if data.get("date"):
        try:
            ans.date = dt.date.fromisoformat(data["date"][:10])
        except ValueError:
            pass
    ans.table = {r["name"]: r["value"] for r in data.get("table") or []}
    ans.refused = bool(data.get("refused"))
    cites = data.get("citations") or []
    has = sourced and bool(cites)
    if ans.value is not None:
        ans.shown.append(Shown(label="answer", value=ans.value, sourced=has, defined=defined, sources=cites))
    ans.shown += [Shown(label=k, value=v, sourced=has, defined=defined) for k, v in ans.table.items()]
    ans.item_sources = {i: has for i in ans.items}
    ans.allowed_numbers += [ans.value] if ans.value is not None else []
    return ans
