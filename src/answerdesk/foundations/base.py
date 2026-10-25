"""Shared pieces for the five arms."""
from __future__ import annotations

import time

import yaml

from .. import llm, nlu
from ..answer import DISCLAIMER, Answer, Step, guard
from ..semantic.layer import registry

INTENT_SYSTEM = ("You read a portfolio question from a senior leader at a large LP into fixed fields. "
                 "Fill only what the question says. Dates as YYYY-MM-DD.")


def menu_text() -> str:
    """What the AI sees in C and D: governed metrics and dimensions, nothing else."""
    reg = registry()["metrics"]
    lines = []
    for k, m in reg.items():
        v = max(m["versions"])
        lines.append(f"- {k} (v{v}, owner {m['owner']}, unit {m['unit']}): {m['versions'][v]['plain']} "
                     f"Dimensions: {', '.join(m['dimensions'])}.")
    return "\n".join(lines)


class Foundation:
    key = "?"
    name = "?"
    calls_per_answer = 1

    def __init__(self, store, role: str = "analyst"):
        self.store = store
        self.role = role
        self.live = llm.available()

    # one shared reader of the question, so understanding is never what separates the arms
    def read(self, text: str, prev) -> tuple[nlu.Intent, Step]:
        t0 = time.perf_counter()
        if self.live:
            try:
                data, use = llm.ask_json(INTENT_SYSTEM + " Today is 2026-10-26. Performance metrics default to "
                                         "2026-09-30 unless the question gives a date or says today.",
                                         f"Previous intent: {prev.model_dump_json() if prev else 'none'}\nQuestion: {text}",
                                         intent_schema())
                it = nlu.Intent(**{k: v for k, v in data.items() if v not in (None, [], "")})
                self._usage = [use]
                return it, Step(name="AI reads the question (live)", input=text,
                                output=it.model_dump_json(exclude_defaults=True),
                                ms=use["seconds"] * 1000, tokens=use["input_tokens"] + use["output_tokens"])
            except Exception as e:  # fall back to the offline reader, and say so
                self._fallback = f"live read failed ({type(e).__name__}); offline reader used"
        it = nlu.parse(text, prev)
        return it, Step(name="read the question", input=text, output=it.model_dump_json(exclude_defaults=True),
                        ms=(time.perf_counter() - t0) * 1000)

    def prompt(self, text: str) -> str:
        return INTENT_SYSTEM + "\n" + text

    def ask(self, text: str, prev=None, role: str | None = None) -> tuple[Answer, nlu.Intent]:
        if role and role != self.role:
            return type(self)(self.store, role).ask(text, prev)
        t0 = time.perf_counter()
        it, s0 = self.read(text, prev)
        ans = self.answer(text, it)
        ans.steps.insert(0, s0)
        ans.role = self.role
        ans.foundation = self.key
        ans.question = text
        ans.llm_calls = self.calls_per_answer
        ans.prompt_chars = len(self.prompt(text)) + sum(len(s.input) for s in ans.steps[1:] if s.name.startswith("AI"))
        ans.compute_s = time.perf_counter() - t0
        ans.as_of = it.as_of
        if self.live:
            uses = getattr(self, "_usage", [])
            ans.live = True
            ans.live_tokens_in = sum(x["input_tokens"] for x in uses)
            ans.live_tokens_out = sum(x["output_tokens"] for x in uses)
            ans.live_seconds = sum(x["seconds"] for x in uses)
            ans.llm_calls = len(uses)
            self._usage = []
        if DISCLAIMER not in ans.text:
            ans.text = f"{ans.text}\n\n{DISCLAIMER}"
        return guard(ans), it

    def answer(self, text: str, it: nlu.Intent) -> Answer:  # pragma: no cover
        raise NotImplementedError


def intent_schema() -> dict:
    """Strict JSON schema for the Intent fields (every field required, null allowed)."""
    props = {}
    for name, f in nlu.Intent.model_fields.items():
        ann = str(f.annotation)
        if "list" in ann:
            props[name] = {"type": "array", "items": {"type": "string"}}
        elif "bool" in ann:
            props[name] = {"type": "boolean"}
        elif "int" in ann:
            props[name] = {"type": ["integer", "null"]}
        else:
            props[name] = {"type": ["string", "null"]}
    return llm.strict({"type": "object", "properties": props, "required": list(props)})


def refuse(key: str, reason: str, who: str = "") -> Answer:
    txt = f"I can't answer this. {reason}" + (f" Ask {who}." if who else "")
    return Answer(foundation=key, question="", text=txt, refused=True, reason=reason, who_can=who)


def dump(obj) -> str:
    return yaml.safe_dump(obj, sort_keys=False, default_flow_style=False)[:2000]
