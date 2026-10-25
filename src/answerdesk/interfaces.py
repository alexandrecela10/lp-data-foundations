"""The four front ends, as plain functions the app and the tests both call.

- chat: one question in, one sendable answer out (foundation D).
- dashboard: three governed views (exposure, funds against plan, cash next 12 months), as of a date.
- notebook: read-only SQL on the role's copy of gold.
- briefing note: a manager's history with sources, as Markdown.
"""
from __future__ import annotations

import datetime as dt
import re

import pandas as pd

from . import access, graph
from .answer import DISCLAIMER, money, pct, ratio
from .foundations import ARMS
from .semantic.layer import MetricRequest, SemanticLayer, changes_since

LAST_PACK = dt.date(2026, 6, 30)


def chat(store, question: str, role: str = "analyst", arm: str = "D", prev=None):
    return ARMS[arm](store, role).ask(question, prev)


def copy_text(ans, note: str = "") -> str:
    """What 'Copy answer to send' puts on the clipboard."""
    parts = [ans.text.replace(DISCLAIMER, "").strip()]
    if ans.definitions:
        parts.append("Definitions: " + ", ".join(ans.definitions))
    if ans.freshness:
        parts.append("Freshness: " + "; ".join(f"{k} {v}" for k, v in ans.freshness.items() if v))
    if note:
        parts.append(f"Note from Sara: {note}")
    parts.append(DISCLAIMER)
    return "\n\n".join(parts)


# ------------------------------------------------------------------ dashboard
def dashboard(store, role: str = "analyst", as_of: dt.date = dt.date(2026, 9, 30), pack: str | None = None) -> dict:
    sl = SemanticLayer(store, role, "resolved")
    top = sl.run(MetricRequest(metric="lookthrough_exposure", as_of=as_of, top_n=10))
    exposure = pd.DataFrame([dict(company=n.label, exposure_usd_m=round(n.value, 3)) for n in top.numbers])
    sectors = {}
    for r in sl.exposure_rows(as_of):
        if r["sector"]:
            sectors[(r["sector"], r["region"])] = sectors.get((r["sector"], r["region"]), 0.0) + r["value"]
    sector = pd.DataFrame([dict(sector=s, region=g, exposure_usd_m=round(v, 3)) for (s, g), v in
                           sorted(sectors.items(), key=lambda kv: -kv[1])])
    rows = []
    base = dict(as_of=as_of, pack=pack)
    per = {}
    for m in ["commitment", "net_irr", "net_tvpi", "net_dpi", "tvpi_vs_plan", "unfunded", "calls_next_12m"]:
        res = sl.run(MetricRequest(metric=m, group_by="fund", **base))
        for i in res.items:
            per.setdefault(i["fund"], {})[m] = i["value"]
    funds = sl.scope(MetricRequest(metric="net_tvpi", as_of=as_of))
    meta = {f["name"]: f for f in funds}
    for name, vals in per.items():
        f = meta.get(name, {})
        rows.append(dict(fund=name, vintage=f.get("vintage"), strategy=f.get("strategy"),
                         commitment=vals.get("commitment"), net_irr=vals.get("net_irr"), net_tvpi=vals.get("net_tvpi"),
                         net_dpi=vals.get("net_dpi"), vs_plan=vals.get("tvpi_vs_plan"), unfunded=vals.get("unfunded"),
                         calls_next_12m=vals.get("calls_next_12m")))
    perf = pd.DataFrame(rows)
    defs = {m: sl.plain(m, max(_versions(m))) for m in
            ["lookthrough_exposure", "net_irr", "net_tvpi", "net_dpi", "tvpi_vs_plan", "unfunded", "calls_next_12m"]}
    return dict(exposure=exposure, sector=sector, performance=perf, definitions=defs,
                changes=changes_since(LAST_PACK), as_of=as_of)


def _versions(metric):
    from .semantic.layer import registry
    return registry()["metrics"][metric]["versions"].keys()


def export_pack(dash: dict) -> str:
    """CSV of the funds view with definitions, versions and the disclaimer in the footer."""
    csv = dash["performance"].to_csv(index=False)
    foot = [f"# As of {dash['as_of']}"] + [f"# {k}: {v}" for k, v in dash["definitions"].items()]
    foot += [f"# Changed since last pack: {c['metric']} v{c['version']} from {c['from_']}" for c in dash["changes"]]
    foot.append(f"# {DISCLAIMER}")
    return csv + "\n".join(foot) + "\n"


# ------------------------------------------------------------------ notebook
SAFE = re.compile(r"^\s*(with|select)\b", re.I)


def notebook(store, sql: str, role: str = "analyst", limit: int = 200) -> pd.DataFrame:
    """Read-only SQL on the role's copy of gold. Only SELECT or WITH queries run."""
    if not SAFE.match(sql) or re.search(r";\s*\S", sql.strip().rstrip(";")):
        raise ValueError("Only one SELECT (or WITH ... SELECT) query runs here.")
    con = access.role_db(store, role)
    return con.execute(f"SELECT * FROM ({sql.strip().rstrip(';')}) LIMIT {limit}").df()


# ------------------------------------------------------------------ briefing note
def briefing(store, manager: str = "Brennick", role: str = "analyst", as_of: dt.date = dt.date(2026, 10, 26)) -> str:
    arm = ARMS["D"](store, role)
    hist, _ = arm.ask(f"{manager} Capital Partners is raising its next fund. What is our history with them?")
    moves, _ = arm.ask(f"Which of our other managers employ former {manager} partners?")
    fees, _ = arm.ask(f"What fees do we pay on our {manager} co-investments?")
    lines = [f"# Briefing: {manager} Capital Partners", "",
             f"**Decision this informs:** whether to commit to {manager}'s next fund. "
             f"**Prepared for:** the head of private equity. **As of:** {as_of:%d %B %Y}.", "",
             "## History, results and issues", hist.text.replace(DISCLAIMER, "").strip(), "",
             "## People", moves.text.replace(DISCLAIMER, "").strip() or "No moves found.", "",
             "## Co-investment fee terms", fees.text.replace(DISCLAIMER, "").strip(), "",
             "## Sources", ", ".join(sorted({s for sh in hist.shown for s in sh.sources} | set(hist.item_sources)))[:1500]
             or "See each line.", "", f"_{DISCLAIMER}_"]
    return "\n".join(lines)
