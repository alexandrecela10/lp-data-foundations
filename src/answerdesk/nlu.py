"""Offline stand-in for the AI's first job: read the question into an intent.

Every foundation gets the same intent, so reading the question is never what separates them;
what they can do with it is. Live mode replaces this with Claude filling the same fields (llm.py).
Rules are written against question wording in general, not against question ids.
"""
from __future__ import annotations

import datetime as dt
import re

from pydantic import BaseModel, Field

from .world import PACK_DATE, TODAY

MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
          "november", "december"]
SECTORS = ["packaging", "software", "health", "foods", "dental", "analytics", "labs", "marine", "fibre", "tools",
           "education", "payments", "chemicals", "clinics", "logistics", "security", "testing", "pet care"]
REGIONS = {"european": "europe", "europe": "europe", "north american": "north_america", "asian": "asia"}
COUNTRIES = ["United Kingdom", "Germany", "France", "Spain", "Netherlands", "United States", "Canada", "Japan"]
ROMANS = r"(?:I|II|III|IV|V|VI|VII|VIII|IX|X)"
STOP = {"How", "What", "Which", "Where", "Did", "Has", "Was", "Should", "And", "After", "Pooled", "News", "Brennick's",
        "Through", "When", "Is", "Are", "Do", "Does", "Can", "Show", "Give", "Tell", "List", "Please", "Who", "Why",
        "Have", "Had", "Will", "Would", "Could", "Our", "Total", "Look-through", "Yes", "No", "Then", "Also",
        "European", "We", "Our", "Fund", "Net", "IRR", "TVPI", "DPI", "PME", "MSCI", "World", "The", "Rerun"}


class Intent(BaseModel):
    task: str = "unknown"            # exposure, exposure_share, routes_managers, routes_funds, top, learnt, perf,
                                     # behind_plan, issues, coinvests, fees, planned, people_moves, people_where,
                                     # history, changes, advice, news_number, unknown_metric
    metric: str | None = None
    company: str | None = None
    sector: str | None = None
    region: str | None = None
    country: str | None = None
    strategy: str | None = None
    vintage_from: int | None = None
    vintage_to: int | None = None
    manager: str | None = None
    fund: str | None = None
    person: str | None = None
    as_of: dt.date = TODAY
    as_of_given: bool = False
    period_start: dt.date | None = None
    period_end: dt.date | None = None
    exclude_route_kinds: list[str] = Field(default_factory=list)
    exclude_companies: list[str] = Field(default_factory=list)
    only_route_kinds: list[str] = Field(default_factory=list)
    group_by: str = "none"
    top_n: int | None = None
    pack: str | None = None
    issue_kinds: list[str] = Field(default_factory=list)
    follow_up: bool = False


def _dates(text: str) -> list[dt.date]:
    out = []
    for d, m, y in re.findall(r"(\d{1,2}) (" + "|".join(MONTHS) + r") (\d{4})", text, re.I):
        out.append(dt.date(int(y), MONTHS.index(m.lower()) + 1, int(d)))
    return out


def _spans(text: str) -> list[str]:
    """Runs of capitalised words, keeping abbreviations like 'Pack.' and fund numbers like 'V'."""
    out = []
    for m in re.finditer(r"[A-Z][\w\-]*\.?(?:\s+[A-Z][\w\-]*\.?)*", text):
        words = m.group(0).split()
        while words and (words[0].rstrip(".") in STOP or words[0] in STOP):
            words.pop(0)
        while words and words[-1] in ("MSCI", "World"):
            words.pop()
        s = " ".join(words).rstrip("?,").strip()
        if s and s not in ROMANS.strip("(?:)").split("|"):
            out.append(s)
    return out


def parse(text: str, prev: Intent | None = None) -> Intent:
    t = text.strip()
    lo = t.lower()
    # follow-ups reuse the last intent and change one thing
    if prev is not None and re.match(r"^(and|what about|now)\b", lo):
        it = prev.model_copy(deep=True)
        it.follow_up = True
        m = re.search(r"excluding (.+?)\??$", t, re.I)
        if m:
            what = m.group(1).strip().rstrip("?")
            if "co-invest" in what.lower():
                it.exclude_route_kinds.append("coinvest")
            elif "fund of funds" in what.lower() or "funds of funds" in what.lower():
                it.exclude_route_kinds.append("fof")
            else:
                it.exclude_companies.append(what)
        return it

    it = Intent()
    ds = _dates(t)
    if ds:
        it.as_of, it.as_of_given = ds[-1], True
    q = re.search(r"(first|second|third|fourth) quarter of (\d{4})", lo)
    if q:
        n = ["first", "second", "third", "fourth"].index(q.group(1))
        y = int(q.group(2))
        it.period_start = dt.date(y, 3 * n + 1, 1)
        end_m = 3 * n + 3
        it.period_end = dt.date(y, end_m, 31 if end_m in (3, 12) else 30)
        it.as_of, it.as_of_given = it.period_end, True

    vm = re.search(r"(20\d\d)\s*(?:to|-|–)\s*(20\d\d)", t)
    if vm:
        it.vintage_from, it.vintage_to = int(vm.group(1)), int(vm.group(2))
    if "buyout" in lo:
        it.strategy = "buyout"
    for k, v in REGIONS.items():
        if re.search(rf"\b{k}\b", lo):
            it.region = v
    for c in COUNTRIES:
        if c.lower() in lo:
            it.country = c
    for s in SECTORS:
        if re.search(rf"\b{s} companies\b", lo):
            it.sector = s.title()

    spans = _spans(t)
    for s in spans:
        if re.search(rf"(Capital|Growth) Partners {ROMANS}$|Ventures {ROMANS}$|Funds {ROMANS}$", s):
            it.fund = s
        elif re.search(r"(Capital|Growth) Partners$|^Brennick$|^Halvane$|^Selbrook$", s) or s in ("Brennick",):
            it.manager = s
    if not it.manager and it.fund:
        it.manager = re.sub(rf"\s+{ROMANS}$", "", it.fund)
    if re.search(r"\bbrennick\b", lo) and not it.manager:
        it.manager = "Brennick"

    def company_span():
        for s in spans:
            if s in (it.fund, it.manager) or s in COUNTRIES or s.startswith("Brennick") or "Partners" in s:
                continue
            if re.fullmatch(r"[A-Z]\w+ ?(?:[A-Z][\w\-]*\.?)?(?: (?:Ltd|Holdings|Inc\.|BV|SA|GmbH))?", s) and len(s) > 3:
                return s
        return None

    # ---- task
    if re.search(r"what fees|fees do we pay|fee terms|carried interest", lo):
        it.task = "fees"
    elif re.search(r"plann?ing to commit|plan to commit|proposed commitment", lo):
        it.task = "planned"
    elif re.search(r"should we (invest|commit)|do you recommend", lo):
        it.task = "advice"
    elif lo.startswith("news says") or "the news" in lo:
        it.task = "news_number"
        it.company = company_span()
    elif re.search(r"\bpme\b|public market equivalent", lo):
        it.task, it.metric = "unknown_metric", "pme"
    elif "gross irr" in lo:
        it.task, it.metric = "unknown_metric", "gross_irr"
    elif re.search(r"definition.* chang|chang.* definition", lo):
        it.task = "changes"
    elif re.search(r"history with", lo):
        it.task = "history"
    elif re.search(r"where did (.+?) go", lo):
        it.task = "people_where"
        it.person = re.search(r"where did (.+?) go", t, re.I).group(1)
    elif re.search(r"former .*partners|ex-partners", lo):
        it.task = "people_moves"
    elif re.search(r"co-investments?\b.*(made|done|have) with|what co-investments", lo):
        it.task = "coinvests"
    elif re.search(r"issues?|restated|key person|team change|raised in", lo):
        it.task = "issues"
        if "restated" in lo:
            it.issue_kinds = ["restatement"]
        elif "key person" in lo or "team change" in lo:
            it.issue_kinds = ["team_change"]
    elif re.search(r"through which managers", lo):
        it.task, it.company = "routes_managers", company_span()
    elif re.search(r"which of our funds hold", lo):
        it.task, it.company = "routes_funds", company_span()
    elif re.search(r"top (\d+) companies", lo):
        it.task, it.top_n = "top", int(re.search(r"top (\d+)", lo).group(1))
    elif re.search(r"did we know|first learn|in trouble", lo):
        it.task, it.company = "learnt", company_span()
    elif re.search(r"share of our total portfolio", lo):
        it.task, it.company = "exposure_share", company_span()
    elif re.search(r"expos|have in|hold in", lo) and not re.search(
            r"unfunded|\birr\b|tvpi|\bdpi\b|multiple of our money|distribut|called|committed to|against plan|"
            r"behind plan|next 12 months|worth", lo):
        it.task = "exposure"
        if not it.sector:
            it.company = company_span()
        if re.search(r"through funds? of funds", lo):
            it.only_route_kinds = ["fof"]
    else:
        it.task = "perf"

    # ---- performance metric
    if it.task in ("perf", "history"):
        if re.search(r"against plan|behind plan|compare to plan|versus plan", lo):
            it.metric = "tvpi_vs_plan"
            if "behind plan" in lo:
                it.task = "behind_plan"
        elif re.search(r"call(ed)? in the next 12 months|be called in the next|calls? next 12", lo):
            it.metric = "calls_next_12m"
        elif "unfunded" in lo:
            it.metric = "unfunded"
        elif re.search(r"\birr\b", lo):
            it.metric = "net_irr"
        elif re.search(r"\bdpi\b", lo):
            it.metric = "net_dpi"
        elif re.search(r"tvpi|multiple of our money", lo):
            it.metric = "net_tvpi"
        elif re.search(r"distribut", lo):
            it.metric = "distributions"
        elif re.search(r"capital (was )?called|called from us", lo):
            it.metric = "calls"
        elif re.search(r"committed to", lo):
            it.metric = "commitment"
        elif re.search(r"worth|value today|nav\b", lo):
            it.metric = "adjusted_nav"
        elif it.task == "perf":
            it.task = "unknown_metric"
        if re.search(r"\beach\b|fund by fund", lo):
            it.group_by = "fund"
        if "last quarter's pack" in lo or "last quarter's definition" in lo:
            it.pack = "pack_2026_q2"
        if not it.as_of_given:
            # performance is reported as of the last quarter end, unless the question says today
            it.as_of = TODAY if re.search(r"\btoday\b|right now", lo) else PACK_DATE
    return it
