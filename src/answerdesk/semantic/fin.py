"""Pure, tested functions behind each governed metric. No database, no I/O."""
from __future__ import annotations

import datetime as dt

CALL_RATES = [(2, 0.35), (4, 0.25), (6, 0.12), (999, 0.05)]


def xirr(cfs: list[tuple[dt.date, float]]) -> float | None:
    """Annual rate r with sum(cf / (1+r)^years) = 0, by bisection on [-99%, +1000%].
    None ("not meaningful") when flows never change sign or no root is bracketed."""
    if not cfs or min(a for _, a in cfs) >= 0 or max(a for _, a in cfs) <= 0:
        return None
    t0 = min(d for d, _ in cfs)

    def npv(r: float) -> float:
        return sum(a / (1 + r) ** ((d - t0).days / 365.25) for d, a in cfs)

    lo, hi = -0.99, 10.0
    flo, fhi = npv(lo), npv(hi)
    if flo * fhi > 0:
        return None
    for _ in range(200):
        mid = (lo + hi) / 2
        fm = npv(mid)
        if flo * fm <= 0:
            hi = mid
        else:
            lo, flo = mid, fm
    return (lo + hi) / 2


def adjusted_nav(reported_nav: float, report_date: dt.date | None, flows: list[dict]) -> float:
    nav = reported_nav
    for f in flows:
        if report_date is None or f["value_date"] > report_date:
            if f["kind"] == "call":
                nav += f["amount"]
            elif f["kind"] == "dist":
                nav -= f["amount"]
    return nav


def paid_in(flows: list[dict]) -> float:
    return sum(f["amount"] for f in flows if f["kind"] in ("call", "purchase"))


def distributions(flows: list[dict], start: dt.date | None = None, end: dt.date | None = None) -> float:
    return sum(f["amount"] for f in flows if f["kind"] == "dist"
               and (start is None or f["value_date"] >= start) and (end is None or f["value_date"] <= end))


def calls(flows: list[dict], start: dt.date | None = None, end: dt.date | None = None) -> float:
    return sum(f["amount"] for f in flows if f["kind"] == "call"
               and (start is None or f["value_date"] >= start) and (end is None or f["value_date"] <= end))


def unfunded(base_commitment: float, flows: list[dict], version: int) -> float:
    u = base_commitment - sum(f["amount"] for f in flows if f["kind"] == "call")
    if version >= 2:
        u += sum(f["recallable"] for f in flows if f["kind"] == "dist")
    return max(u, 0.0)


def fund_age(vintage: int, d: dt.date) -> float:
    return (d - dt.date(vintage, 1, 1)).days / 365.25


def call_rate(age: float) -> float:
    return next(r for lim, r in CALL_RATES if age < lim)


def plan_tvpi(target: float, age: float) -> float:
    return 1 + (target - 1) * min(max((age - 2) / 8, 0.0), 1.0)


def irr_flows(flows: list[dict], d: dt.date, nav: float) -> list[tuple[dt.date, float]]:
    out = [(f["value_date"], -f["amount"] if f["kind"] in ("call", "purchase") else f["amount"]) for f in flows]
    out.append((d, nav))
    return out
