"""The semantic layer: a small YAML metric registry compiled to SQL over gold.

The AI (or its offline stand-in) never writes SQL here. It fills a MetricRequest from a menu of
governed metrics and dimensions; this module checks the request, checks access, compiles it and
computes. Unknown metric: refuse. Restricted table for the role: refuse and name who can see it.

identity="exact"     company names match only after normalising (foundation C)
identity="resolved"  names go through the identity table: holding companies, abbreviations (C+ids, D)
"""
from __future__ import annotations

import datetime as dt
import re
from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field

from .. import access
from ..pipeline import normalise
from . import fin

REGISTRY_PATH = Path(__file__).with_name("metrics.yaml")
ISSUE_KINDS = ("extension", "restatement", "team_change", "write_down", "exit", "incident", "concern")


@lru_cache(maxsize=1)
def registry() -> dict:
    return yaml.safe_load(REGISTRY_PATH.read_text())


class MetricRequest(BaseModel):
    metric: str
    as_of: dt.date
    version: int | None = None
    pack: str | None = None
    company: str | None = None
    sector: str | None = None
    region: str | None = None
    country: str | None = None
    exclude_route_kinds: list[str] = Field(default_factory=list)
    exclude_companies: list[str] = Field(default_factory=list)
    strategy: str | None = None
    vintage_from: int | None = None
    vintage_to: int | None = None
    manager: str | None = None
    fund: str | None = None
    period_start: dt.date | None = None
    period_end: dt.date | None = None
    group_by: Literal["none", "fund", "route", "company"] = "none"
    top_n: int | None = None


class Number(BaseModel):
    label: str
    value: float | None
    unit: str
    as_of: dt.date | None = None          # date of the oldest report behind it
    sources: list[str] = Field(default_factory=list)
    definition: str = ""                  # metric@version
    plain: str = ""


class Result(BaseModel):
    request: dict
    numbers: list[Number] = Field(default_factory=list)
    items: list[dict] = Field(default_factory=list)
    pending: list[dict] = Field(default_factory=list)
    refused: bool = False
    reason: str = ""
    who_can: str = ""
    sql: str = ""
    freshness: dict = Field(default_factory=dict)
    definitions: list[str] = Field(default_factory=list)


def version_for(metric: str, req: MetricRequest) -> int:
    reg = registry()
    m = reg["metrics"][metric]
    if req.version:
        return req.version
    if req.pack:
        return reg["packs"][req.pack]["versions"].get(metric, max(m["versions"]))
    return max(m["versions"])


def changes_since(d: dt.date) -> list[dict]:
    out = []
    for name, m in registry()["metrics"].items():
        for v, spec in m["versions"].items():
            f = spec["from"]
            f = f if isinstance(f, dt.date) else dt.date.fromisoformat(str(f))
            if f > d:
                out.append(dict(metric=name, version=v, from_=f, plain=spec["plain"]))
    return out


EXPOSURE_SQL = """
WITH RECURSIVE
rep AS (SELECT fund_id, max(as_of) AS q FROM gold.reports WHERE as_of <= $d AND learnt <= $d GROUP BY fund_id),
lp_share AS (SELECT r.fund_id, r.lp_share, r.doc_id FROM gold.reports r JOIN rep ON rep.fund_id = r.fund_id AND r.as_of = rep.q),
stake_q AS (SELECT fof_id, max(as_of) AS q FROM gold.fof_stakes WHERE as_of <= $d AND learnt <= $d GROUP BY fof_id),
stakes AS (SELECT s.fof_id, s.fund_id, s.share, s.doc_id FROM gold.fof_stakes s JOIN stake_q q ON q.fof_id = s.fof_id AND s.as_of = q.q),
walk(position_id, route_kind, vehicle_id, mult, depth, path, docs) AS (
    SELECT p.position_id,
           CASE WHEN p.vehicle_type = 'fof' THEN 'fof' WHEN p.acquired = 'secondary' THEN 'secondary' ELSE 'fund' END,
           p.vehicle_id, l.lp_share, 1, [p.vehicle_id], [l.doc_id]
    FROM gold.positions p JOIN lp_share l ON l.fund_id = p.vehicle_id
    WHERE p.vehicle_type IN ('fund', 'fof') AND p.start_date <= $d
  UNION ALL
    SELECT w.position_id, w.route_kind, s.fund_id, w.mult * s.share, w.depth + 1,
           list_append(w.path, s.fund_id), list_append(w.docs, s.doc_id)
    FROM walk w JOIN stakes s ON s.fof_id = w.vehicle_id
    WHERE w.depth < 5 AND NOT list_contains(w.path, s.fund_id)          -- depth limit and cycle guard
),
hq AS (SELECT fund_id, max(as_of) AS q FROM gold.holdings WHERE as_of <= $d AND learnt <= $d GROUP BY fund_id),
hv AS (
    SELECT h.* FROM gold.holdings h JOIN hq ON hq.fund_id = h.fund_id AND h.as_of = hq.q
    WHERE h.learnt <= $d
    QUALIFY row_number() OVER (PARTITION BY h.fund_id, h.name_reported ORDER BY CASE h.via WHEN 'own' THEN 0 ELSE 1 END) = 1
),
ev AS (SELECT * FROM gold.events WHERE status = 'accepted' AND kind IN ('write_down', 'exit') AND learnt <= $d),
fund_routes AS (
    SELECT w.position_id, w.route_kind, w.path, h.fund_id, h.name_reported, h.{cid} AS company_id, h.as_of,
           h.value * w.mult AS raw_value,
           coalesce((SELECT CASE WHEN bool_or(e.kind = 'exit') THEN 0 ELSE exp(sum(ln(e.factor))) END
                     FROM ev e WHERE e.event_fund_id = h.fund_id AND e.effective > h.as_of
                       AND e.{cid} IS NOT NULL AND e.{cid} = h.{cid}), 1.0) AS factor,
           list_append(w.docs, h.doc_id) AS docs
    FROM walk w JOIN hv h ON h.fund_id = w.vehicle_id
    WHERE h.{cid} IS NOT NULL
),
cq AS (SELECT coinvest_id, max(as_of) AS q FROM gold.coinvest_values WHERE as_of <= $d AND learnt <= $d GROUP BY coinvest_id),
co_routes AS (
    SELECT p.position_id, 'coinvest' AS route_kind, [c.coinvest_id] AS path, NULL AS fund_id, c.name_reported,
           c.{cid} AS company_id, c.as_of, c.value AS raw_value,
           coalesce((SELECT CASE WHEN bool_or(e.kind = 'exit') THEN 0 ELSE exp(sum(ln(e.factor))) END
                     FROM ev e WHERE e.event_coinvest_id = c.coinvest_id AND e.effective > c.as_of), 1.0) AS factor,
           [c.doc_id] AS docs
    FROM gold.coinvest_values c JOIN cq ON cq.coinvest_id = c.coinvest_id AND c.as_of = cq.q
    JOIN gold.positions p ON p.vehicle_id = c.coinvest_id AND p.start_date <= $d
    WHERE c.{cid} IS NOT NULL
)
SELECT r.*, r.raw_value * r.factor AS value, co.name AS company_name, co.sector, co.region, co.country
FROM (SELECT * FROM fund_routes UNION ALL SELECT * FROM co_routes) r
LEFT JOIN gold.companies co ON co.company_id = r.company_id
"""


class SemanticLayer:
    def __init__(self, store, role: str = "analyst", identity: str = "exact"):
        self.store = store
        self.role = role
        self.identity = identity
        self.con = access.role_db(store, role)

    # ---------------------------------------------------------- helpers
    @property
    def cid(self) -> str:
        return "company_id" if self.identity == "resolved" else "company_id_exact"

    def resolve_company(self, name: str) -> tuple[str | None, str]:
        """Company id for a name, and how it was matched."""
        key = normalise(name)
        rows = self.con.execute("SELECT company_id, is_holdco, name FROM gold.companies WHERE name_key = ?", [key]).fetchall()
        if self.identity == "exact":
            ops = [r for r in rows if not r[1]]
            return (ops[0][0], "exact") if len(ops) == 1 else (None, "no exact match")
        if len(rows) == 1 and not rows[0][1]:
            return rows[0][0], "exact"
        hit = self.con.execute("SELECT company_id, method FROM gold.identity WHERE name_key = ? AND status = 'accepted'",
                               [key]).fetchall()
        if hit:
            return hit[0][0], hit[0][1]
        if len(rows) == 1 and rows[0][1]:
            kids = self.con.execute("SELECT company_id FROM gold.companies WHERE parent_id = ?", [rows[0][0]]).fetchall()
            if len(kids) == 1:
                return kids[0][0], "holding company"
        toks = key.split()
        if name.strip().endswith(".") and len(toks) >= 2:
            cands = [cid for cid, k in self.con.execute("SELECT company_id, name_key FROM gold.companies WHERE NOT is_holdco").fetchall()
                     if k.split()[:-1] == toks[:-1] and len(k.split()) == len(toks) and k.split()[-1].startswith(toks[-1])]
            if len(cands) == 1:
                return cands[0], "abbreviation"
        return None, "no match"

    def _refuse(self, req, reason, who=""):
        return Result(request=req.model_dump(mode="json"), refused=True, reason=reason, who_can=who)

    def _defn(self, metric, v):
        return f"{metric} v{v}"

    def plain(self, metric, v):
        return registry()["metrics"][metric]["versions"][v]["plain"]

    # ---------------------------------------------------------- entry point
    def run(self, req: MetricRequest) -> Result:
        reg = registry()["metrics"]
        if req.metric not in reg:
            return self._refuse(req, f"No governed definition of '{req.metric}'. Ask the metric owners to add one.",
                                "the data team")
        m = reg[req.metric]
        for t in m["needs"]:
            if not access.visible(self.role, t):
                return self._refuse(req, f"Your role ({access.ROLES[self.role]['label']}) can't see {t.replace('_', ' ')}.",
                                    access.WHO_CAN.get(t, "the data owner"))
        v = version_for(req.metric, req)
        fn = getattr(self, f"_m_{req.metric}", None)
        res = fn(req, v)
        res.definitions = sorted(set(res.definitions + [self._defn(req.metric, v)]))
        return res

    # ---------------------------------------------------------- exposure
    def exposure_rows(self, d: dt.date) -> list[dict]:
        sql = EXPOSURE_SQL.replace("{cid}", self.cid)
        cur = self.con.execute(sql, {"d": d})
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]

    def _m_lookthrough_exposure(self, req: MetricRequest, v: int) -> Result:
        d = req.as_of
        if v == 1:
            return self._exposure_v1(req)
        rows = self.exposure_rows(d)
        target = None
        if req.company:
            target, how = self.resolve_company(req.company)
            if target is None:
                return Result(request=req.model_dump(mode="json"), reason=f"No company matching '{req.company}' ({how}).",
                              sql=EXPOSURE_SQL.replace("{cid}", self.cid))
            rows = [r for r in rows if r["company_id"] == target]
        if req.sector:
            rows = [r for r in rows if (r["sector"] or "").lower() == req.sector.lower()]
        if req.region:
            rows = [r for r in rows if r["region"] == req.region]
        if req.country:
            rows = [r for r in rows if r["country"] == req.country]
        if req.exclude_companies:
            ex = {self.resolve_company(n)[0] for n in req.exclude_companies}
            rows = [r for r in rows if r["company_id"] not in ex]
        rows = [r for r in rows if r["route_kind"] not in req.exclude_route_kinds]
        names = self._vehicle_names()
        items = []
        for r in sorted(rows, key=lambda r: -r["value"]):
            items.append(dict(route=" > ".join(["Aldermoor"] + [names.get(x, x) for x in r["path"]] +
                                               [r["company_name"] or r["name_reported"]]),
                              kind=r["route_kind"], recorded_as=r["name_reported"], value=r["value"],
                              before_events=r["raw_value"], factor=r["factor"], as_of=r["as_of"],
                              company_id=r["company_id"], company=r["company_name"], sources=list(r["docs"])))
        pending = self._pending(d, target)
        docs = sorted({s for it in items for s in it["sources"]})
        oldest = min((it["as_of"] for it in items), default=None)
        if req.group_by == "company" or req.top_n:
            agg: dict = {}
            for it in items:
                agg.setdefault(it["company_id"], [it["company"], 0.0])[1] += it["value"]
            ranked = sorted(agg.items(), key=lambda kv: -kv[1][1])[: req.top_n or None]
            nums = [Number(label=n, value=val, unit="$m", definition=self._defn(req.metric, v),
                           plain=self.plain(req.metric, v)) for _, (n, val) in ranked]
            return Result(request=req.model_dump(mode="json"), numbers=nums,
                          items=[dict(company_id=k, company=n, value=val) for k, (n, val) in ranked],
                          sql=EXPOSURE_SQL.replace("{cid}", self.cid))
        total = sum(it["value"] for it in items)
        label = req.company or " ".join(x for x in [req.region, req.country, req.sector] if x) or "portfolio"
        num = Number(label=f"Look-through exposure, {label}", value=total, unit="$m", as_of=oldest, sources=docs,
                     definition=self._defn(req.metric, v), plain=self.plain(req.metric, v))
        return Result(request=req.model_dump(mode="json"), numbers=[num], items=items, pending=pending,
                      sql=EXPOSURE_SQL.replace("{cid}", self.cid), freshness=self._freshness(d))

    def _exposure_v1(self, req: MetricRequest) -> Result:
        target, _ = self.resolve_company(req.company or "")
        d = req.as_of
        rows = self.con.execute(f"""
            WITH hq AS (SELECT fund_id, max(as_of) q FROM gold.holdings WHERE as_of <= $d AND learnt <= $d AND via = 'own' GROUP BY fund_id)
            SELECT p.commitment, h.value / r.fund_nav AS weight, h.doc_id
            FROM gold.positions p JOIN hq ON hq.fund_id = p.vehicle_id
            JOIN gold.holdings h ON h.fund_id = hq.fund_id AND h.as_of = hq.q AND h.via = 'own'
            JOIN gold.reports r ON r.fund_id = h.fund_id AND r.as_of = h.as_of
            WHERE p.vehicle_type = 'fund' AND p.start_date <= $d AND h.{self.cid} = $c""", {"d": d, "c": target}).fetchall()
        val = sum(c * w for c, w, _ in rows)
        return Result(request=req.model_dump(mode="json"), numbers=[Number(
            label=f"Exposure (commitment-based, v1), {req.company}", value=val, unit="$m",
            sources=[r[2] for r in rows], definition=self._defn("lookthrough_exposure", 1),
            plain=self.plain("lookthrough_exposure", 1))])

    def _pending(self, d, company_id=None) -> list[dict]:
        rows = self.con.execute(f"""SELECT kind, company_name, quote, learnt, doc_id, {self.cid}
            FROM gold.events WHERE status = 'waiting_for_review' AND learnt <= ?""", [d]).fetchall()
        return [dict(kind=k, company=c, quote=q, learnt=l, source=s) for k, c, q, l, s, cid in rows
                if company_id is None or cid == company_id or (c and company_id and normalise(c).split()[0] ==
                                                             (self._company_name(company_id) or "").lower().split()[0])]

    def _company_name(self, cid):
        r = self.con.execute("SELECT name FROM gold.companies WHERE company_id = ?", [cid]).fetchone()
        return r[0] if r else None

    def _vehicle_names(self) -> dict:
        names = dict(self.con.execute("SELECT fund_id, name FROM gold.funds").fetchall())
        names.update(dict(self.con.execute(
            "SELECT vehicle_id, 'Co-investment ' || split_part(vehicle_name, ' (', 1) FROM gold.positions WHERE vehicle_type = 'coinvest'").fetchall()))
        return names

    def _freshness(self, d: dt.date) -> dict:
        out = {}
        for label, sql in [("holdings", "SELECT max(start_date) FROM gold.positions"),
                           ("fund reports", "SELECT max(learnt) FROM gold.reports WHERE learnt <= $d"),
                           ("latest report date", "SELECT max(as_of) FROM gold.reports WHERE learnt <= $d"),
                           ("letters", "SELECT max(learnt) FROM gold.letters WHERE learnt <= $d"),
                           ("notices", "SELECT max(notice_date) FROM gold.cashflows WHERE notice_date <= $d")]:
            try:
                out[label] = self.con.execute(sql, {"d": d} if "$d" in sql else {}).fetchone()[0]
            except Exception:
                out[label] = None
        return out

    # ---------------------------------------------------------- performance
    def scope(self, req: MetricRequest) -> list[dict]:
        rows = self.con.execute("""SELECT p.position_id, p.vehicle_id, p.vehicle_type, p.acquired, p.commitment,
               p.start_date, p.purchase_price, p.unfunded_at_purchase, p.plan_tvpi, f.name, f.vintage, f.strategy,
               f.manager_id, m.name AS manager
            FROM gold.positions p LEFT JOIN gold.funds f ON f.fund_id = p.vehicle_id
            LEFT JOIN gold.managers m ON m.manager_id = coalesce(f.manager_id, p.manager_id)
            WHERE p.start_date <= ? ORDER BY p.position_id""", [req.as_of]).fetchall()
        cols = ["position_id", "vehicle_id", "vehicle_type", "acquired", "commitment", "start_date", "purchase_price",
                "unfunded_at_purchase", "plan_tvpi", "name", "vintage", "strategy", "manager_id", "manager"]
        out = []
        filtered = any([req.strategy, req.vintage_from, req.manager, req.fund])
        for r in rows:
            r = dict(zip(cols, r))
            if r["vehicle_type"] == "coinvest":
                continue
            if r["vehicle_type"] == "fof" and filtered:
                continue
            if req.strategy and r["strategy"] != req.strategy:
                continue
            if req.vintage_from and not (req.vintage_from <= r["vintage"] <= (req.vintage_to or 9999)):
                continue
            if req.manager and not _same(req.manager, r["manager"]):
                continue
            if req.fund and not _same_fund(req.fund, r["name"]):
                continue
            out.append(r)
        return out

    def _flows(self, pid: str, d: dt.date) -> list[dict]:
        cur = self.con.execute("""SELECT kind, amount, recallable, value_date, doc_id FROM gold.cashflows
            WHERE position_id = ? AND value_date <= ? AND notice_date <= ?""", [pid, d, d])
        return [dict(kind=k, amount=a, recallable=r, value_date=v, doc_id=s) for k, a, r, v, s in cur.fetchall()]

    def _reported(self, pos: dict, d: dt.date) -> tuple[float, dt.date | None, str | None]:
        r = self.con.execute("""SELECT lp_nav, as_of, doc_id FROM gold.reports WHERE fund_id = ? AND as_of <= ?
            AND learnt <= ? AND as_of >= ? ORDER BY as_of DESC LIMIT 1""",
                             [pos["vehicle_id"], d, d, pos["start_date"]]).fetchone()
        return (r[0], r[1], r[2]) if r else (0.0, None, None)

    def _perf(self, req: MetricRequest):
        d = req.as_of
        out = []
        for p in self.scope(req):
            fl = self._flows(p["position_id"], d)
            nav, q, doc = self._reported(p, d)
            out.append(dict(pos=p, flows=fl, nav=fin.adjusted_nav(nav, q, fl), report=q, doc=doc))
        return out

    def _result(self, req, v, label, unit, per: list, agg_value):
        nums = []
        if req.group_by == "fund":
            for x in per:
                nums.append(Number(label=x["pos"]["name"], value=x["value"], unit=unit, as_of=x["report"],
                                   sources=[s for s in [x["doc"]] if s] + [f["doc_id"] for f in x["flows"][-3:]],
                                   definition=self._defn(req.metric, v), plain=self.plain(req.metric, v)))
        else:
            srcs = sorted({x["doc"] for x in per if x["doc"]})
            oldest = min((x["report"] for x in per if x["report"]), default=None)
            nums.append(Number(label=label, value=agg_value, unit=unit, as_of=oldest, sources=srcs,
                               definition=self._defn(req.metric, v), plain=self.plain(req.metric, v)))
        items = [dict(fund=x["pos"]["name"], value=x["value"], report=x["report"]) for x in per]
        return Result(request=req.model_dump(mode="json"), numbers=nums, items=items, freshness=self._freshness(req.as_of))

    def _m_adjusted_nav(self, req, v):
        per = self._perf(req)
        for x in per:
            x["value"] = x["nav"]
        if not req.fund and not req.manager and not req.strategy:   # whole portfolio includes co-investments
            for cv in self.con.execute("""SELECT c.value FROM gold.coinvest_values c JOIN (SELECT coinvest_id, max(as_of) q
                    FROM gold.coinvest_values WHERE as_of <= $d AND learnt <= $d GROUP BY 1) m
                    ON m.coinvest_id = c.coinvest_id AND m.q = c.as_of""", {"d": req.as_of}).fetchall():
                per.append(dict(pos=dict(name="co-investment"), flows=[], value=cv[0], report=None, doc=None))
        return self._result(req, v, "Adjusted NAV", "$m", per, sum(x["value"] for x in per))

    def _m_paid_in(self, req, v):
        per = self._perf(req)
        for x in per:
            x["value"] = fin.paid_in(x["flows"])
        return self._result(req, v, "Paid-in", "$m", per, sum(x["value"] for x in per))

    def _m_distributions(self, req, v):
        per = self._perf(req)
        for x in per:
            x["value"] = fin.distributions(x["flows"], req.period_start, req.period_end)
        return self._result(req, v, "Distributions", "$m", per, sum(x["value"] for x in per))

    def _m_calls(self, req, v):
        per = self._perf(req)
        for x in per:
            x["value"] = fin.calls(x["flows"], req.period_start, req.period_end)
        return self._result(req, v, "Capital calls", "$m", per, sum(x["value"] for x in per))

    def _m_commitment(self, req, v):
        per = self._perf(req)
        for x in per:
            x["value"] = x["pos"]["commitment"]
        return self._result(req, v, "Commitment", "$m", per, sum(x["value"] for x in per))

    def _m_net_tvpi(self, req, v):
        per = self._perf(req)
        for x in per:
            pi = fin.paid_in(x["flows"])
            x["value"] = (fin.distributions(x["flows"]) + x["nav"]) / pi if pi else None
        pi = sum(fin.paid_in(x["flows"]) for x in per)
        agg = sum(fin.distributions(x["flows"]) + x["nav"] for x in per) / pi if pi else None
        return self._result(req, v, "Net TVPI (pooled)", "x", per, agg)

    def _m_net_dpi(self, req, v):
        per = self._perf(req)
        for x in per:
            pi = fin.paid_in(x["flows"])
            x["value"] = fin.distributions(x["flows"]) / pi if pi else None
        pi = sum(fin.paid_in(x["flows"]) for x in per)
        agg = sum(fin.distributions(x["flows"]) for x in per) / pi if pi else None
        return self._result(req, v, "Net DPI (pooled)", "x", per, agg)

    def _m_net_irr(self, req, v):
        per = self._perf(req)
        allc = []
        for x in per:
            c = fin.irr_flows(x["flows"], req.as_of, x["nav"])
            allc += c
            x["value"] = fin.xirr(c)
        return self._result(req, v, "Net IRR (pooled)", "%", per, fin.xirr(allc))

    def _m_unfunded(self, req, v):
        per = self._perf(req)
        for x in per:
            p = x["pos"]
            base = p["unfunded_at_purchase"] if p["acquired"] == "secondary" else p["commitment"]
            x["value"] = fin.unfunded(base, x["flows"], v)
        return self._result(req, v, f"Unfunded (v{v})", "$m", per, sum(x["value"] for x in per))

    def _m_calls_next_12m(self, req, v):
        per = self._perf(req)
        for x in per:
            p = x["pos"]
            base = p["unfunded_at_purchase"] if p["acquired"] == "secondary" else p["commitment"]
            x["value"] = fin.unfunded(base, x["flows"], 2) * fin.call_rate(fin.fund_age(p["vintage"], req.as_of))
        return self._result(req, v, "Calls expected in the next 12 months", "$m", per, sum(x["value"] for x in per))

    def _m_tvpi_vs_plan(self, req, v):
        per = self._perf(req)
        for x in per:
            p = x["pos"]
            pi = fin.paid_in(x["flows"])
            tv = (fin.distributions(x["flows"]) + x["nav"]) / pi if pi else 0.0
            x["value"] = tv - fin.plan_tvpi(p["plan_tvpi"], fin.fund_age(p["vintage"], req.as_of))
        return self._result(req, v, "TVPI against plan", "x", per, None if len(per) != 1 else per[0]["value"])

    # ---------------------------------------------------------- lists
    def _manager_id(self, name: str | None) -> str | None:
        if not name:
            return None
        for mid, mname in self.con.execute("SELECT manager_id, name FROM gold.managers").fetchall():
            if _same(name, mname):
                return mid
        return None

    def _m_manager_issues(self, req, v):
        mid = self._manager_id(req.manager)
        rows = self.con.execute("""SELECT kind, quote, learnt, doc_id, status FROM gold.events
            WHERE manager_id = ? AND learnt <= ? AND kind IN ('extension','restatement','team_change','write_down','incident','concern')
            ORDER BY learnt""", [mid, req.as_of]).fetchall()
        items = [dict(kind=k, quote=q, learnt=l, source=s) for k, q, l, s, st in rows if st == "accepted"]
        pending = [dict(kind=k, quote=q, learnt=l, source=s) for k, q, l, s, st in rows if st != "accepted"]
        return Result(request=req.model_dump(mode="json"), items=items, pending=pending)

    def _m_coinvest_positions(self, req, v):
        mid = self._manager_id(req.manager)
        rows = self.con.execute("""SELECT split_part(vehicle_name, ' (', 1), commitment, doc_id FROM gold.positions
            WHERE vehicle_type = 'coinvest' AND (? IS NULL OR manager_id = ?) AND start_date <= ?""",
                                [mid, mid, req.as_of]).fetchall()
        return Result(request=req.model_dump(mode="json"), items=[dict(name=n, invested=c, source=s) for n, c, s in rows])

    def _m_coinvest_fees(self, req, v):
        mid = self._manager_id(req.manager)
        rows = self.con.execute("""SELECT split_part(p.vehicle_name, ' (', 1), f.mgmt_fee_pct, f.carry_pct, f.doc_id
            FROM gold.coinvest_fees f JOIN gold.positions p ON p.vehicle_id = f.coinvest_id
            WHERE (? IS NULL OR p.manager_id = ?)""", [mid, mid]).fetchall()
        return Result(request=req.model_dump(mode="json"),
                      items=[dict(name=n, mgmt_fee_pct=a, carry_pct=b, source=s) for n, a, b, s in rows])

    def _m_planned_commitment(self, req, v):
        mid = self._manager_id(req.manager)
        rows = self.con.execute("SELECT fund_name, proposed_commitment, doc_id FROM gold.planned WHERE ? IS NULL OR manager_id = ?",
                                [mid, mid]).fetchall()
        return Result(request=req.model_dump(mode="json"), numbers=[Number(
            label=f"Planned commitment, {r[0]}", value=r[1], unit="$m", sources=[r[2]],
            definition=self._defn("planned_commitment", v), plain=self.plain("planned_commitment", v)) for r in rows])


def _same(a: str, b: str | None) -> bool:
    """Manager match: equal after normalising, or the first words of the name ("Brennick")."""
    if not b:
        return False
    na, nb = normalise(a), normalise(b)
    return na == nb or (len(na) > 3 and nb.startswith(na + " "))


def _same_fund(a: str, b: str | None) -> bool:
    return bool(b) and normalise(a) == normalise(b)
