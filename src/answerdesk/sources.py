"""Render the six sources the LP actually receives, each with its rhythm and dates.

| Source | Rhythm | Shape |
|---|---|---|
| holdings (accounting system) | daily snapshot | rows |
| notices (capital calls, distributions) | when they happen, about weekly | email + PDF text |
| reports (fund quarterly reports, co-investment statements) | quarterly, 40 to 90 days late | text, one layout per manager |
| letters (manager letters) | whenever | free text |
| reference (companies, parents, managers, funds, people) | slow-changing | rows |
| news (synthetic headlines) | every 15 minutes | free text, never a source of numbers |

Every document carries `learnt_at` (when it reached us) and, where it has one, `as_of`.
Rendering is deterministic: same seed, same bytes.
"""
from __future__ import annotations

import datetime as dt
import random
from dataclasses import dataclass, field

from .truth import STATEMENT_LAG, coinvest_value, xirr
from .world import FIRST_REPORT_Q, LP_NAME, TODAY, World, quarter_ends

SCHEDULE = {
    "holdings": "daily, snapshot at 06:00",
    "notices": "when a manager sends one, about weekly",
    "reports": "quarterly, 40 to 90 days after quarter end",
    "letters": "whenever a manager writes",
    "reference": "slow-changing, refreshed monthly",
    "news": "every 15 minutes",
}


@dataclass
class Doc:
    doc_id: str
    source: str
    learnt_at: dt.date
    text: str = ""
    as_of: dt.date | None = None
    row: dict = field(default_factory=dict)
    restricted_to: tuple = ()       # roles that may see it; empty = everyone
    kind: str = ""                  # finer type inside a source


def _money(x_m: float) -> str:
    return f"{x_m:,.2f}"


def _usd(x_m: float) -> str:
    return f"USD {x_m * 1e6:,.2f}"


def _d(d: dt.date) -> str:
    return f"{d.day} {d:%B %Y}"


def fund_reported_irr(w: World, fid: str, q: dt.date) -> float | None:
    """The manager's own fund-level IRR, quarterly flows, with a credit-line effect (+2.5 points)."""
    f = w.funds[fid]
    prev = (0.0, 0.0, 0.0)
    cfs = []
    for d in sorted(x for x in f.path if x <= q):
        c, di, _ = f.path[d]
        cfs.append((d, -(c - prev[0]) + (di - prev[1])))
        prev = f.path[d]
    cfs.append((q, f.path[q][2]))
    r = xirr(cfs)
    return None if r is None else r + 0.025


def report_text(w: World, fid: str, q: dt.date, share: float) -> str:
    f = w.funds[fid]
    m = w.managers[f.manager_id]
    c, di, nav = f.path[q]
    irr = fund_reported_irr(w, fid, q)
    tv = (di + nav) / c if c else 0.0
    irr_s = f"{irr * 100:.1f}%" if irr is not None else "n/m"
    lines = sorted(f.weights.items(), key=lambda kv: -kv[1])
    if m.layout == 0:
        out = [f"{f.name.upper()}", f"Quarterly report to investors, as of {_d(q)}",
               f"Vintage {f.vintage} | Strategy: {f.strategy} | Fund size: ${_money(f.size)}m",
               f"Fund net asset value: ${_money(nav)}m",
               f"Net IRR since inception (fund level, incl. credit facility): {irr_s}",
               f"Net TVPI (fund level): {tv:.2f}x", "Your capital account", f"  Investor: {LP_NAME}",
               f"  Your share of the fund: {share * 100:.4f}%", f"  Your net asset value: ${_money(share * nav)}m",
               "Portfolio", "| Company | Sector | Country | Fair value ($m) |"]
        for cid, wt in lines:
            co = w.companies[cid]
            out.append(f"| {w.spelling(m.id, cid)} | {co.sector} | {co.country} | {_money(wt * nav)} |")
    elif m.layout == 1:
        out = [f"{f.name} - Investor Report", f"Period end: {q.isoformat()}",
               f"Vintage: {f.vintage}; strategy: {f.strategy}",
               f"NAV (USD m): {nav:.2f} ; Reported net IRR: {irr_s} ; Reported net TVPI: {tv:.2f}x",
               f"Capital account of {LP_NAME}: ownership {share * 100:.4f}% ; NAV USD {share * nav:.2f}m", "Holdings:"]
        for cid, wt in lines:
            out.append(f"- {w.spelling(m.id, cid)} - USD {wt * nav:.2f}m")
    else:
        out = [f"{f.name.upper()};REPORT;{q.isoformat()}", f"vintage;{f.vintage}", f"strategy;{f.strategy}",
               f"fund_nav_usd_m;{nav:.2f}", f"reported_net_irr;{irr_s}", f"reported_net_tvpi;{tv:.2f}",
               f"lp_name;{LP_NAME}", f"lp_ownership_pct;{share * 100:.4f}", f"lp_nav_usd_m;{share * nav:.2f}"]
        for cid, wt in lines:
            out.append(f"holding;{w.spelling(m.id, cid)};{wt * nav:.2f}")
    return "\n".join(out)


def fof_report_text(w: World, fid: str, q: dt.date, share: float) -> str:
    f = w.funds[fid]
    nav = f.path[q][2]
    out = [f"{f.name}, quarterly statement, as of {_d(q)}", f"Vintage {f.vintage}. Strategy: fund of funds.",
           f"Fund of funds net asset value: ${_money(nav)}m",
           f"Your share of the fund of funds: {share * 100:.4f}%. Your net asset value: ${_money(share * nav)}m.",
           "Underlying funds"]
    for u, s in sorted(f.stakes.items()):
        uf = w.funds[u]
        out.append(f"* {uf.name}: Selbrook share {s * 100:.4f}%, value to Selbrook ${_money(s * uf.path[q][2])}m")
    out.append("Look-through holdings of underlying funds (fund | company as reported by its manager | value in that fund, $m)")
    for u, _ in sorted(f.stakes.items()):
        uf = w.funds[u]
        for cid, wt in sorted(uf.weights.items(), key=lambda kv: -kv[1]):
            out.append(f"* {uf.name} | {w.spelling(uf.manager_id, cid)} | {wt * uf.path[q][2]:.2f}")
    return "\n".join(out)


def render(w: World) -> list[Doc]:
    rng = random.Random(w.seed + 101)
    docs: list[Doc] = []
    snap = TODAY - dt.timedelta(days=1)

    # 1. holdings: daily snapshot rows (co-investment fee terms are restricted columns)
    for p in sorted(w.positions.values(), key=lambda p: p.id):
        if p.vehicle_type == "coinvest":
            c = w.coinvests[p.vehicle_id]
            name, mgr = c.name_on_docs, w.funds[c.alongside_fund_id].manager_id
        else:
            name, mgr = w.funds[p.vehicle_id].name, w.funds[p.vehicle_id].manager_id
        row = dict(position_id=p.id, vehicle_id=p.vehicle_id, vehicle_name=name, vehicle_type=p.vehicle_type,
                   manager_id=mgr, acquired=p.acquired, commitment=round(p.commitment, 6), start_date=p.start,
                   purchase_price=round(p.purchase_price, 6), unfunded_at_purchase=round(p.unfunded_at_purchase, 6),
                   plan_tvpi=p.plan_tvpi, plan_irr=p.plan_irr, status="active")
        if p.vehicle_type == "coinvest":
            row.update(mgmt_fee_pct=c.mgmt_fee_pct, carry_pct=c.carry_pct)
        docs.append(Doc(f"HOLD:{p.id}:{snap}", "holdings", snap, row=row, as_of=snap, kind="position"))
    for i, pl in enumerate(w.pipeline):
        docs.append(Doc(f"HOLD:PLAN{i}:{snap}", "holdings", snap, row=dict(pl), as_of=snap, kind="planned",
                        restricted_to=("head_of_pe",)))

    # 2. notices
    for fl in sorted(w.flows, key=lambda f: (f.notice_date, f.id)):
        p = w.positions[fl.position_id]
        if p.vehicle_type == "coinvest":
            vname = w.coinvests[p.vehicle_id].name_on_docs
            dom = w.managers[w.funds[w.coinvests[p.vehicle_id].alongside_fund_id].manager_id].domain
        else:
            vname = w.funds[p.vehicle_id].name
            dom = w.managers[w.funds[p.vehicle_id].manager_id].domain
        if fl.kind == "purchase":
            text = (f"From: transfers@secondaries-desk.example\nSubject: Completion statement, purchase of an interest in {vname}\n"
                    f"Investor: {LP_NAME}\nReference: {fl.id}\nCompletion date: {fl.value_date.isoformat()}\n"
                    f"Purchase price paid: {_usd(fl.amount)}\n")
        elif fl.kind == "call":
            text = (f"From: capital.calls@{dom}\nSubject: Capital call notice, {vname}\nInvestor: {LP_NAME}\n"
                    f"Reference: {fl.id}\nNotice date: {fl.notice_date.isoformat()}\n"
                    f"Amount due: {_usd(fl.amount)}\nDue date: {fl.value_date.isoformat()}\n"
                    "--- attached PDF text ---\nPurpose: investments and fees.\n")
        else:
            text = (f"From: distributions@{dom}\nSubject: Distribution notice, {vname}\nInvestor: {LP_NAME}\n"
                    f"Reference: {fl.id}\nNotice date: {fl.notice_date.isoformat()}\n"
                    f"Distribution date: {fl.value_date.isoformat()}\nAmount: {_usd(fl.amount)}\n"
                    f"Of which recallable: {_usd(fl.recallable)}\n--- attached PDF text ---\nSource: realisations.\n")
        if rng.random() < 0.02 and fl.kind != "purchase":
            # a malformed notice (European number format), then a corrected one two days later
            bad = text.replace(_usd(fl.amount), "USD " + f"{fl.amount * 1e6:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            docs.append(Doc(f"NOT:{fl.id}", "notices", fl.notice_date, bad, kind=fl.kind))
            docs.append(Doc(f"NOT:{fl.id}:R", "notices", fl.notice_date + dt.timedelta(days=2),
                            text.replace("Subject: ", "Subject: CORRECTED "), kind=fl.kind))
        else:
            docs.append(Doc(f"NOT:{fl.id}", "notices", fl.notice_date, text, kind=fl.kind))

    # 3. reports: each fund we hold, from FIRST_REPORT_Q, arriving lag days late
    held = {}
    for p in w.positions.values():
        if p.vehicle_type in ("fund", "fof"):
            held[p.vehicle_id] = p
    for fid, p in sorted(held.items()):
        f = w.funds[fid]
        for q in sorted(f.path):
            if q < FIRST_REPORT_Q or q < p.start:
                continue
            learnt = q + dt.timedelta(days=f.report_lag[q])
            if learnt > TODAY:
                continue
            text = fof_report_text(w, fid, q, p.share) if f.kind == "fof" else report_text(w, fid, q, p.share)
            docs.append(Doc(f"REP:{fid}:{q}", "reports", learnt, text, as_of=q, kind="fund_report"))
    for cid, c in sorted(w.coinvests.items()):
        mgr = w.managers[w.funds[c.alongside_fund_id].manager_id]
        for q in quarter_ends(max(FIRST_REPORT_Q, c.date), TODAY):
            learnt = q + dt.timedelta(days=STATEMENT_LAG)
            if learnt > TODAY:
                continue
            v = coinvest_value(w, cid, q)
            text = (f"Co-investment statement: {c.name_on_docs}\nReference: {cid}\n"
                    f"Alongside: {w.funds[c.alongside_fund_id].name}. Sponsor: {mgr.name}. As of {_d(q)}.\n"
                    f"Investor: {LP_NAME}\nYour investment at cost: ${_money(c.invested)}m. Your value: ${_money(v)}m.")
            docs.append(Doc(f"COS:{cid}:{q}", "reports", learnt, text, as_of=q, kind="coinvest_statement"))
        docs.append(Doc(f"FEE:{cid}", "reports", c.date, (
            f"Co-investment fee schedule: {c.name_on_docs}\nReference: {cid}\nSponsor: {mgr.name}\n"
            f"Management fee: {c.mgmt_fee_pct:.2f}% a year. Carried interest: {c.carry_pct:.1f}%."),
            as_of=c.date, kind="coinvest_fees", restricted_to=("head_of_pe",)))

    # 4. letters
    for lid, l in sorted(w.letters.items()):
        docs.append(Doc(f"LET:{lid}", "letters", l.learnt,
                        f"From: {w.managers[l.manager_id].name}\nDate: {l.learnt.isoformat()}\n{l.text}", kind="letter"))

    # 5. reference rows
    ref_date = dt.date(2026, 10, 1)
    for c in sorted(w.companies.values(), key=lambda c: c.id):
        docs.append(Doc(f"REF:CO:{c.id}", "reference", ref_date, row=dict(
            company_id=c.id, name=c.name, sector=c.sector, country=c.country, region=c.region,
            parent_id=c.parent_id or "", is_holdco=c.is_holdco), kind="company"))
    for m in sorted(w.managers.values(), key=lambda m: m.id):
        docs.append(Doc(f"REF:MG:{m.id}", "reference", ref_date, row=dict(
            manager_id=m.id, name=m.name, strategy=m.strategy, region=m.region, kind=m.kind), kind="manager"))
    for f in sorted(w.funds.values(), key=lambda f: f.id):
        docs.append(Doc(f"REF:FD:{f.id}", "reference", ref_date, row=dict(
            fund_id=f.id, manager_id=f.manager_id, name=f.name, vintage=f.vintage, strategy=f.strategy,
            region=f.region, size=f.size, kind=f.kind), kind="fund"))
    for pe in sorted(w.people.values(), key=lambda p: p.id):
        for j, (mid, s, e, title) in enumerate(pe.jobs):
            docs.append(Doc(f"REF:PE:{pe.id}:{j}", "reference", ref_date, row=dict(
                person_id=pe.id, name=pe.name, manager_id=mid, start=s, end=e, title=title), kind="person"))
    # the company reference also comes as a readable sheet, so a documents-only reader can use it
    for c in sorted(w.companies.values(), key=lambda c: c.id):
        if c.is_holdco:
            kids = [k for k in w.companies.values() if k.parent_id == c.id]
            if kids:
                docs.append(Doc(f"REFTXT:{c.id}", "reference", ref_date,
                                f"Company reference: {c.name} is a holding company. Its only asset is {kids[0].name} "
                                f"({kids[0].sector}, {kids[0].country}).", kind="company_text"))

    # 6. news
    for n in w.news:
        docs.append(Doc(f"NEWS:{n.id}", "news", n.ts.date(), f"{n.ts:%Y-%m-%d %H:%M} {n.headline}. {n.body}",
                        kind="news", row=dict(ts=n.ts)))
    return docs
