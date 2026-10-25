"""The answer every foundation returns, the number checker (guardrail) and the checking-time model.

Checking-time model (ASSUMED, to be refitted by the timed human run):
- 20 s to read any answer;
- 5 s per number shown with a source and a governed definition;
- 30 s per number shown with a source but no definition (she opens the passage);
- 120 s per number she must verify by hand (no source, or SQL output with no definition);
- per listed item: 5 s with a source, 60 s without;
- a correct refusal: 20 s to read plus 30 s to forward to the person named.
A wrong answer is a fail, however fast. Model time per AI call when offline: 3.0 s (ASSUMED).
"""
from __future__ import annotations

import datetime as dt
import re

from pydantic import BaseModel, Field

DISCLAIMER = "Synthetic data. Not investment advice."
CHECK = dict(read=20.0, sourced_defined=5.0, sourced=30.0, by_hand=120.0, item_sourced=5.0, item_unsourced=60.0,
             forward_refusal=30.0)
ASSUMED_SECONDS_PER_CALL = 3.0
PRICE_IN, PRICE_OUT = 2.0 / 1e6, 10.0 / 1e6        # claude-sonnet-5-5, $ per token
ASSUMED_OUTPUT_TOKENS = 300


class Shown(BaseModel):
    label: str
    value: float | None
    unit: str = ""
    sourced: bool = False
    defined: bool = False
    sources: list[str] = Field(default_factory=list)
    as_of: dt.date | None = None


class Step(BaseModel):
    name: str
    input: str = ""
    output: str = ""
    ms: float = 0.0
    tokens: int = 0
    cost: float = 0.0


class Answer(BaseModel):
    foundation: str
    question: str
    role: str = "analyst"
    text: str = ""
    value: float | None = None
    items: list[str] = Field(default_factory=list)
    item_sources: dict = Field(default_factory=dict)
    date: dt.date | None = None
    table: dict = Field(default_factory=dict)
    composite: dict = Field(default_factory=dict)
    routes: list[dict] = Field(default_factory=list)
    route_sigs: list[str] = Field(default_factory=list)
    refused: bool = False
    reason: str = ""
    who_can: str = ""
    shown: list[Shown] = Field(default_factory=list)
    definitions: list[str] = Field(default_factory=list)
    pending: list[dict] = Field(default_factory=list)
    freshness: dict = Field(default_factory=dict)
    sql: str = ""
    as_of: dt.date | None = None
    llm_calls: int = 0
    prompt_chars: int = 0
    live: bool = False
    compute_s: float = 0.0
    steps: list[Step] = Field(default_factory=list)
    check_passed: bool = True
    live_tokens_in: int = 0
    live_tokens_out: int = 0
    live_seconds: float = 0.0
    allowed_numbers: list[float] = Field(default_factory=list)

    # ---------------------------------------------------------- costs and time
    @property
    def tokens_in(self) -> int:
        return self.prompt_chars // 4

    @property
    def cost_usd(self) -> float:
        if self.live:
            return self.live_tokens_in * PRICE_IN + self.live_tokens_out * PRICE_OUT
        return self.llm_calls and (self.tokens_in * PRICE_IN + self.llm_calls * ASSUMED_OUTPUT_TOKENS * PRICE_OUT) or 0.0

    @property
    def latency_s(self) -> float:
        model = 0.0 if self.live else self.llm_calls * ASSUMED_SECONDS_PER_CALL
        return self.compute_s + model

    def checking_s(self, k: dict | None = None) -> float:
        k = {**CHECK, **(k or {})}
        if self.refused:
            return k["read"] + k["forward_refusal"]
        t = k["read"]
        for s in self.shown:
            if s.sourced and s.defined:
                t += k["sourced_defined"]
            elif s.sourced:
                t += k["sourced"]
            else:
                t += k["by_hand"]
        for it in self.items:
            t += k["item_sourced"] if self.item_sources.get(it) else k["item_unsourced"]
        if self.date and not self.shown:
            t += k["item_sourced"] if self.item_sources.get("date") else k["item_unsourced"]
        return t


NUM = re.compile(r"(?<![\w.])-?\$?\d[\d,]*(?:\.\d+)?(?:%|x|m)?")


def numbers_in(text: str) -> list[float]:
    out = []
    for tok in NUM.findall(text):
        s = tok.replace("$", "").replace(",", "").rstrip("%xm")
        try:
            out.append(float(s))
        except ValueError:
            pass
    return out


def check_numbers(text: str, allowed: list[float], tol: float = 0.006) -> list[float]:
    """Every number in the final text must be one we computed or read from a source (or a year,
    a day of the month, a count). Returns the numbers that fail; an empty list passes."""
    bad = []
    for x in numbers_in(text):
        if x.is_integer() and (1900 <= x <= 2100 or 0 <= x <= 31):
            continue
        ok = any(abs(x - a) <= max(tol * abs(a), 0.006) for a in allowed)
        if not ok:
            bad.append(x)
    return bad


def guard(ans: Answer) -> Answer:
    """Fail closed: if any number in the text isn't in the allowed set, the answer is withheld."""
    allowed = list(ans.allowed_numbers)
    for s in ans.shown:
        if s.value is not None:
            allowed += [s.value, round(s.value, 2), round(s.value, 1), s.value * 100]
    allowed += [v for v in ans.table.values() if isinstance(v, (int, float))]
    bad = check_numbers(ans.text, allowed)
    if bad:
        ans.check_passed = False
        ans.text = (f"I couldn't verify every number in this answer ({', '.join(str(b) for b in bad[:3])}), so I'm not "
                    f"showing it. {DISCLAIMER}")
        ans.value, ans.table, ans.items, ans.shown = None, {}, [], []
        ans.refused, ans.reason = True, "number check failed"
    return ans


def money(x: float | None) -> str:
    return "n/a" if x is None else f"${x:,.2f}m"


def ratio(x: float | None) -> str:
    return "n/a" if x is None else f"{x:.2f}x"


def pct(x: float | None) -> str:
    return "not meaningful" if x is None else f"{x * 100:.1f}%"
