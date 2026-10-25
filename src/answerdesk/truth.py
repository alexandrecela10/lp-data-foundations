"""Known answers, computed from the generator's objects only (docs/DEFINITIONS.md).

This module never imports the pipeline, the semantic layer, the graph or any foundation
(tests/test_truth_independent.py checks it). It reads the World the generator built.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from .world import FIRST_REPORT_Q, World, quarter_ends

ISSUE_KINDS = {"extension", "restatement", "team_change", "fee", "incident", "write_down", "concern"}
CALL_RATES = [(2, 0.35), (4, 0.25), (6, 0.12), (999, 0.05)]
STATEMENT_LAG = 40  # days from quarter end to a co-investment statement


@dataclass
class Route:
    vehicles: list          # ids from the LP's position down to the fund holding the company
    company_id: str         # the holding as recorded (may be a holding company)
    value: float
    as_of: dt.date          # report date used
    kind: str               # fund | fof | coinvest | secondary


def report_q(w: World, fid: str, d: dt.date) -> dt.date | None:
    """Latest quarter whose report we had by d."""
    f = w.funds[fid]
    best = None
    for q, lag in f.report_lag.items():
        if FIRST_REPORT_Q <= q <= d and q + dt.timedelta(days=lag) <= d:
            best = q if best is None or q > best else best
    return best


def statement_q(w: World, cid: str, d: dt.date) -> dt.date | None:
    c = w.coinvests[cid]
    best = None
    for q in quarter_ends(max(FIRST_REPORT_Q, c.date), d):
        if q + dt.timedelta(days=STATEMENT_LAG) <= d:
            best = q
    return best


def coinvest_value(w: World, cid: str, q: dt.date) -> float:
    c = w.coinvests[cid]
    years = (q - c.date).days / 365.25
    return c.invested * (1 + c.growth) ** years


def targets(w: World, company_id: str) -> set[str]:
    """The company plus any pure holding company whose only asset is it."""
    t = {company_id}
    c = w.companies[company_id]
    if c.parent_id and w.companies[c.parent_id].is_holdco:
        kids = [k for k in w.companies.values() if k.parent_id == c.parent_id]
        if len(kids) == 1:
            t.add(c.parent_id)
    return t


def _factor(w: World, fund_id: str | None, coinvest_id: str | None, company_ids: set, after: dt.date,
            d: dt.date) -> float:
    f = 1.0
    for e in w.events.values():
        if e.kind not in ("write_down", "exit") or e.confidence < 0.8:
            continue
        if not (after < e.effective and e.learnt <= d):
            continue
        hit = (coinvest_id and coinvest_id in e.coinvest_ids) or (
            fund_id and e.fund_id == fund_id and e.company_id in company_ids)
        if hit:
            f = 0.0 if e.kind == "exit" else f * e.factor
    return f


def exposure_routes(w: World, company_id: str, d: dt.date) -> list[Route]:
    tg = targets(w, company_id)
    routes = []
    direct = {p.vehicle_id for p in w.positions.values() if p.vehicle_type == "fund" and p.start <= d}
    for p in sorted(w.positions.values(), key=lambda p: p.id):
        if p.start > d:
            continue
        if p.vehicle_type == "fund":
            f = w.funds[p.vehicle_id]
            q = report_q(w, f.id, d)
            if q is None:
                continue
            q = max([q] + [fq for fq in (report_q(w, ff, d) for ff in fof_holding(w, f.id, d)) if fq])
            for cid in sorted(tg & set(f.weights)):
                v = f.weights[cid] * f.path[q][2] * p.share * _factor(w, f.id, None, {cid}, q, d)
                routes.append(Route([p.vehicle_id], cid, v, q, "secondary" if p.acquired == "secondary" else "fund"))
        elif p.vehicle_type == "fof":
            fof = w.funds[p.vehicle_id]
            qf = report_q(w, fof.id, d)
            if qf is None:
                continue
            for u, s in sorted(fof.stakes.items()):
                uf = w.funds[u]
                q = qf
                qo = report_q(w, u, d) if u in direct else None
                if qo is not None and qo >= qf:
                    q = qo
                for cid in sorted(tg & set(uf.weights)):
                    v = uf.weights[cid] * uf.path[q][2] * s * p.share * _factor(w, u, None, {cid}, q, d)
                    routes.append(Route([fof.id, u], cid, v, q, "fof"))
        elif p.vehicle_type == "coinvest":
            c = w.coinvests[p.vehicle_id]
            if c.company_id not in tg:
                continue
            q = statement_q(w, c.id, d)
            if q is None:
                continue
            v = coinvest_value(w, c.id, q) * _factor(w, None, c.id, tg, q, d)
            routes.append(Route([c.id], c.company_id, v, q, "coinvest"))
    return routes


def fof_holding(w: World, fund_id: str, d: dt.date) -> list[str]:
    """Funds of funds we hold that hold this fund (their reports carry a copy of its holdings)."""
    return [p.vehicle_id for p in w.positions.values() if p.vehicle_type == "fof" and p.start <= d
            and fund_id in w.funds[p.vehicle_id].stakes]


def exposure(w: World, company_id: str, d: dt.date, exclude: set | None = None) -> float:
    ex = exclude or set()
    return sum(r.value for r in exposure_routes(w, company_id, d) if r.kind not in ex)


def exposure_v1_commitment(w: World, company_id: str, d: dt.date) -> float:
    """Retired v1 (the other team's definition): commitment x the company's share of each direct fund."""
    tg = targets(w, company_id)
    tot = 0.0
    for p in w.positions.values():
        if p.vehicle_type == "fund" and p.start <= d:
            f = w.funds[p.vehicle_id]
            tot += p.commitment * sum(f.weights.get(c, 0.0) for c in tg)
    return tot


def operating_companies(w: World) -> list[str]:
    return sorted(c.id for c in w.companies.values() if not c.is_holdco)


def sector_exposure(w: World, sector: str, d: dt.date, region: str | None = None, country: str | None = None,
                    exclude_companies: set | None = None) -> float:
    tot = 0.0
    for cid in operating_companies(w):
        c = w.companies[cid]
        if c.sector != sector or (region and c.region != region) or (country and c.country != country):
            continue
        if exclude_companies and cid in exclude_companies:
            continue
        tot += exposure(w, cid, d)
    return tot


def top_companies(w: World, d: dt.date, n: int = 5) -> list[str]:
    vals = [(exposure(w, cid, d), cid) for cid in operating_companies(w)]
    vals.sort(reverse=True)
    return [cid for _, cid in vals[:n]]


# ------------------------------------------------------------------ performance

def flows_until(w: World, pid: str, d: dt.date):
    return [f for f in w.flows if f.position_id == pid and f.value_date <= d and f.notice_date <= d]


def lp_reported_nav(w: World, pid: str, d: dt.date) -> tuple[float, dt.date | None]:
    p = w.positions[pid]
    if p.vehicle_type == "coinvest":
        q = statement_q(w, p.vehicle_id, d)
        return (coinvest_value(w, p.vehicle_id, q), q) if q else (0.0, None)
    q = report_q(w, p.vehicle_id, d)
    if q is None or q < p.start:
        return 0.0, None
    return p.share * w.funds[p.vehicle_id].path[q][2], q


def adjusted_nav(w: World, pid: str, d: dt.date) -> float:
    nav, q = lp_reported_nav(w, pid, d)
    for f in flows_until(w, pid, d):
        if q is None or f.value_date > q:
            if f.kind == "call":
                nav += f.amount
            elif f.kind == "dist":
                nav -= f.amount
    return nav


def paid_in(w: World, pid: str, d: dt.date) -> float:
    return sum(f.amount for f in flows_until(w, pid, d) if f.kind in ("call", "purchase"))


def distributions(w: World, pid: str, d: dt.date, start: dt.date | None = None) -> float:
    return sum(f.amount for f in flows_until(w, pid, d) if f.kind == "dist" and (start is None or f.value_date >= start))


def calls_between(w: World, pid: str, start: dt.date, end: dt.date) -> float:
    return sum(f.amount for f in flows_until(w, pid, end) if f.kind == "call" and f.value_date >= start)


def xirr(cfs: list[tuple[dt.date, float]]) -> float | None:
    if not cfs or min(a for _, a in cfs) >= 0 or max(a for _, a in cfs) <= 0:
        return None
    t0 = min(d for d, _ in cfs)

    def npv(r):
        return sum(a / (1 + r) ** ((d - t0).days / 365.25) for d, a in cfs)

    lo, hi = -0.99, 10.0
    flo, fhi = npv(lo), npv(hi)
    if flo * fhi > 0:
        return None
    for _ in range(200):
        mid = (lo + hi) / 2
        fm = npv(mid)
        if flo * fm <= 0:
            hi, fhi = mid, fm
        else:
            lo, flo = mid, fm
    return (lo + hi) / 2


def net_irr(w: World, pid: str, d: dt.date) -> float | None:
    cfs = [(f.value_date, -f.amount if f.kind in ("call", "purchase") else f.amount) for f in flows_until(w, pid, d)]
    cfs.append((d, adjusted_nav(w, pid, d)))
    return xirr(cfs)


def pooled_irr(w: World, pids: list[str], d: dt.date) -> float | None:
    cfs = []
    for pid in pids:
        cfs += [(f.value_date, -f.amount if f.kind in ("call", "purchase") else f.amount) for f in flows_until(w, pid, d)]
        cfs.append((d, adjusted_nav(w, pid, d)))
    return xirr(cfs)


def tvpi(w: World, pid: str, d: dt.date) -> float:
    pi = paid_in(w, pid, d)
    return (distributions(w, pid, d) + adjusted_nav(w, pid, d)) / pi if pi else 0.0


def dpi(w: World, pid: str, d: dt.date) -> float:
    pi = paid_in(w, pid, d)
    return distributions(w, pid, d) / pi if pi else 0.0


def pooled(w: World, pids: list[str], d: dt.date, kind: str) -> float:
    pi = sum(paid_in(w, p, d) for p in pids)
    di = sum(distributions(w, p, d) for p in pids)
    nav = sum(adjusted_nav(w, p, d) for p in pids)
    if kind == "tvpi":
        return (di + nav) / pi
    if kind == "dpi":
        return di / pi
    raise ValueError(kind)


def unfunded(w: World, pid: str, d: dt.date, version: int = 2) -> float:
    p = w.positions[pid]
    if p.vehicle_type == "coinvest":
        return 0.0
    fl = flows_until(w, pid, d)
    base = p.unfunded_at_purchase if p.acquired == "secondary" else p.commitment
    u = base - sum(f.amount for f in fl if f.kind == "call")
    if version == 2:
        u += sum(f.recallable for f in fl if f.kind == "dist")
    return max(u, 0.0)


def fund_age(w: World, pid: str, d: dt.date) -> float:
    p = w.positions[pid]
    v = w.funds[p.vehicle_id].vintage
    return (d - dt.date(v, 1, 1)).days / 365.25


def calls_next_12m(w: World, pid: str, d: dt.date) -> float:
    age = fund_age(w, pid, d)
    rate = next(r for lim, r in CALL_RATES if age < lim)
    return unfunded(w, pid, d, 2) * rate


def plan_tvpi(w: World, pid: str, d: dt.date) -> float:
    p = w.positions[pid]
    return 1 + (p.plan_tvpi - 1) * min(max((fund_age(w, pid, d) - 2) / 8, 0.0), 1.0)


def tvpi_vs_plan(w: World, pid: str, d: dt.date) -> float:
    return tvpi(w, pid, d) - plan_tvpi(w, pid, d)


def our_funds(w: World, d: dt.date, strategy: str | None = None, vintages: tuple | None = None,
              manager_id: str | None = None, include_fof: bool = True) -> list[str]:
    out = []
    for p in sorted(w.positions.values(), key=lambda p: p.id):
        if p.vehicle_type == "coinvest" or p.start > d:
            continue
        if p.vehicle_type == "fof" and (not include_fof or strategy or vintages or manager_id):
            continue
        f = w.funds[p.vehicle_id]
        if strategy and f.strategy != strategy:
            continue
        if vintages and not (vintages[0] <= f.vintage <= vintages[1]):
            continue
        if manager_id and f.manager_id != manager_id:
            continue
        out.append(p.id)
    return out


def total_nav(w: World, d: dt.date) -> float:
    return sum(adjusted_nav(w, pid, d) for pid, p in w.positions.items() if p.start <= d)


# ------------------------------------------------------------------ letters and people

def manager_issues(w: World, manager_id: str, d: dt.date) -> set[str]:
    return {e.letter_id for e in w.events.values()
            if e.manager_id == manager_id and e.kind in ISSUE_KINDS and e.learnt <= d}


def first_learnt(w: World, company_id: str, confident: bool = True) -> dt.date | None:
    ds = [e.learnt for e in w.events.values() if e.company_id == company_id
          and (e.confidence >= 0.8) == confident and e.kind in ("write_down", "concern")]
    return min(ds) if ds else None


def former_partner_destinations(w: World, manager_id: str) -> set[str]:
    out = set()
    for p in w.people.values():
        left = [j for j in p.jobs if j[0] == manager_id and j[2] is not None]
        for j in left:
            out |= {k[0] for k in p.jobs if k[0] != manager_id and k[1] >= j[2]}
    return out
