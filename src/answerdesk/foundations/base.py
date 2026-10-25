"""Shared pieces for the five arms."""
from __future__ import annotations

import time

import yaml

from .. import llm, nlu
from ..answer import DISCLAIMER, Answer, Step, guard
from ..semantic.layer import registry

INTENT_SYSTEM = ("You read a portfolio question from a senior leader at a large LP into fixed fields. "
                 "Fill only what the question says. Dates as YYYY-MM-DD. Leave a field empty (\"\", 0 or []) "
                 "when the question doesn't give it.")

# The same conventions the offline reader (nlu.py) follows, written for the live reader, so neither reader
# knows more than the other. Field names and allowed values only: no answers.
TASKS = {
    "exposure": "how much we hold in a company or sector, across every route",
    "exposure_share": "a company's share of our total portfolio",
    "routes_managers": "through which managers we hold a company",
    "routes_funds": "which of our funds hold a company",
    "top": "our top N companies by exposure (set top_n)",
    "learnt": "when we first learnt a company was in trouble",
    "perf": "a fund performance or cash measure (set metric)",
    "behind_plan": "asks which funds are behind plan (metric tvpi_vs_plan); 'how are they doing against plan' is perf",
    "issues": "issues a manager raised in letters (issue_kinds narrows them)",
    "coinvests": "co-investments made with a manager",
    "fees": "fees or carried interest we pay",
    "planned": "a planned or proposed commitment",
    "people_moves": "where a manager's former partners went",
    "people_where": "where one named person went (set person)",
    "history": "our history with a manager",
    "changes": "how a definition changed",
    "advice": "asks whether we should invest or commit",
    "news_number": "uses a figure from the news",
    "unknown_metric": "asks for a measure not in the list below (set metric to its short name, e.g. pme, gross_irr)",
}
FIELD_GUIDE = (
    "task, one of:\n" + "\n".join(f"- {k}: {v}" for k, v in TASKS.items()) +
    "\nmetric for perf, history and behind_plan, one of: " + ", ".join(
        ["net_irr", "net_tvpi", "net_dpi", "unfunded", "calls_next_12m", "tvpi_vs_plan", "distributions", "calls",
         "commitment", "adjusted_nav"]) + "." +
    "\nsector: one of " + ", ".join(s.title() for s in nlu.SECTORS) + ". Set it only for '<sector> companies'." +
    "\ncountry: one of " + ", ".join(nlu.COUNTRIES) + "." +
    "\nmanager: the manager's full name as written (e.g. 'Selbrook Capital Partners'); fund: a fund name with "
    "its number (e.g. 'Selbrook Capital Partners IV'). When a fund is named, set manager to the fund name without "
    "its number. Only managers and funds go here, never companies." +
    "\ncompany: the company name exactly as written in the question." +
    "\nvintage_from, vintage_to: years from 'X to Y'. top_n: the N in 'top N'." +
    "\nas_of: the date the question gives, with as_of_given true; for 'Q of YYYY' use the quarter's last day and "
    "set period_start and period_end. With no date: for perf, history and behind_plan use 2026-09-30 (the last "
    "quarter end), or 2026-10-26 if the question says today or right now; for other tasks leave as_of empty." +
    "\ngroup_by: 'fund' for 'each fund' or 'fund by fund', else 'none'." +
    "\npack: 'pack_2026_q2' when the question asks for last quarter's pack or definitions, else empty." +
    "\nfollow_up: true when the question starts 'And', 'What about' or 'Now' and changes the previous one; "
    "then copy the previous intent and change only what the question changes. 'Excluding co-investments' adds "
    "coinvest to exclude_route_kinds; 'excluding funds of funds' adds fof; excluding a company adds it to "
    "exclude_companies. 'Through funds of funds' sets only_route_kinds to [fof]; otherwise leave route kinds empty." +
    "\nissue_kinds: only when the question names a kind (restated: restatement; key person or team change: "
    "team_change); otherwise empty. pack applies to performance questions only."
)


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
                data, use = llm.ask_json(INTENT_SYSTEM + " Today is 2026-10-26.\n" + FIELD_GUIDE,
                                         f"Previous intent: {prev.model_dump_json() if prev else 'none'}\nQuestion: {text}",
                                         intent_schema())
                it = intent_from(data)
                self._usage = [use]
                return it, Step(name="AI reads the question (live)", input=text,
                                output=it.model_dump_json(exclude_defaults=True),
                                ms=use["seconds"] * 1000, tokens=use["input_tokens"] + use["output_tokens"])
            except Exception as e:  # fall back to the offline reader, and record it: a live run with failures is invalid
                self.failed("read", e)
        it = nlu.parse(text, prev)
        return it, Step(name="read the question", input=text, output=it.model_dump_json(exclude_defaults=True),
                        ms=(time.perf_counter() - t0) * 1000)

    def failed(self, where: str, e: Exception) -> None:
        self._failures = getattr(self, "_failures", []) + [f"{where}: {type(e).__name__}: {str(e)[:200]}"]

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
            ans.live_failures = getattr(self, "_failures", [])
            self._usage, self._failures = [], []
        if DISCLAIMER not in ans.text:
            ans.text = f"{ans.text}\n\n{DISCLAIMER}"
        return guard(ans), it

    def answer(self, text: str, it: nlu.Intent) -> Answer:  # pragma: no cover
        raise NotImplementedError


ENUMS = {
    "task": list(TASKS),
    "strategy": ["", "buyout", "growth", "venture"],
    "region": ["", "europe", "north_america", "asia"],
    "group_by": ["none", "fund"],
    "pack": ["", "pack_2026_q2", "pack_2026_q3"],
}
ITEM_ENUMS = {
    "exclude_route_kinds": ["fund", "secondary", "fof", "coinvest"],
    "only_route_kinds": ["fund", "secondary", "fof", "coinvest"],
    "issue_kinds": ["extension", "restatement", "team_change", "write_down", "incident", "concern"],
}


def intent_schema() -> dict:
    """Strict JSON schema for the Intent fields. Every field required and never null: empty means "not given".

    The API caps union-typed (nullable) fields at 16; Intent has 18 optional fields, so null is not used.
    """
    props = {}
    for name, f in nlu.Intent.model_fields.items():
        ann = str(f.annotation)
        if "list" in ann:
            items = {"type": "string", **({"enum": ITEM_ENUMS[name]} if name in ITEM_ENUMS else {})}
            props[name] = {"type": "array", "items": items}
        elif "bool" in ann:
            props[name] = {"type": "boolean"}
        elif "int" in ann:
            props[name] = {"type": "integer"}
        else:
            props[name] = {"type": "string", **({"enum": ENUMS[name]} if name in ENUMS else {})}
    return llm.strict({"type": "object", "properties": props, "required": list(props)})


def intent_from(data: dict) -> nlu.Intent:
    """Drop empty values ("", 0, []) so the Intent keeps its defaults."""
    return nlu.Intent(**{k: v for k, v in data.items() if v not in (None, [], "", 0)})


def refuse(key: str, reason: str, who: str = "") -> Answer:
    txt = f"I can't answer this. {reason}" + (f" Ask {who}." if who else "")
    return Answer(foundation=key, question="", text=txt, refused=True, reason=reason, who_can=who)


def dump(obj) -> str:
    return yaml.safe_dump(obj, sort_keys=False, default_flow_style=False)[:2000]
