"""The 60-question test set: 20 per request, with known answers from truth.py.

Kinds: number (value within tolerance; for exposure also the set of routes), set (exact set of
names or letter ids), date, table (one value per fund, all within tolerance), refusal, composite.
Traps are tagged: spelling, role, no_definition, point_in_time, news, follow_up, exit, advice.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

from . import truth as T
from .world import PACK_DATE, TODAY, World


@dataclass
class Question:
    id: str
    request: int
    text: str
    kind: str
    expected: object
    role: str = "analyst"
    tol: float = 0.005            # relative, for numbers; absolute for tables of ratios
    traps: tuple = ()
    follows: str | None = None
    routes: frozenset | None = None   # expected route signatures for exposure questions
    note: str = ""


def route_sigs(w: World, company: str, d: dt.date, kinds_out=(), only=()) -> frozenset:
    out = set()
    for r in T.exposure_routes(w, company, d):
        if r.kind in kinds_out or (only and r.kind not in only):
            continue
        if r.value <= 1e-9:
            continue
        bottom = r.vehicles[-1]
        via = "coinvest" if r.kind == "coinvest" else ("fof" if r.kind == "fof" else "direct")
        out.add(f"{via}:{bottom if via == 'coinvest' else w.funds[bottom].name}")
    return frozenset(out)


def name(w: World, x: str) -> str:
    if x in w.funds:
        return w.funds[x].name
    if x in w.managers:
        return w.managers[x].name
    if x in w.companies:
        return w.companies[x].name
    return x


def build(w: World) -> list[Question]:
    D, P = TODAY, PACK_DATE
    C = "C0001"
    qs: list[Question] = []
    add = qs.append
    b19 = T.our_funds(w, P, "buyout", (2019, 2021))
    allf = T.our_funds(w, P)
    bre = T.our_funds(w, P, manager_id="M02")
    hv_pid = f"P{w.planted['halvane_v']}"

    # ---------------- Request 1: an event (Calder Packaging), the CIO, chat
    sig = route_sigs(w, C, D)
    exp = T.exposure(w, C, D)
    add(Question("R1-01", 1, "How exposed are we to Calder Packaging?", "number", exp, routes=sig))
    add(Question("R1-02", 1, "What is our look-through exposure to Calder Packaging Ltd?", "number", exp, routes=sig))
    add(Question("R1-03", 1, "How much do we have in Calderwick Holdings?", "number", exp, routes=sig, traps=("spelling",)))
    add(Question("R1-04", 1, "What is our exposure to Calder Pack.?", "number", exp, routes=sig, traps=("spelling",)))
    mgrs = set()
    for r in T.exposure_routes(w, C, D):
        for v in r.vehicles:
            if v in w.funds:
                mgrs.add(w.managers[w.funds[v].manager_id].name)
            elif v in w.coinvests:
                mgrs.add(w.managers[w.funds[w.coinvests[v].alongside_fund_id].manager_id].name)
    add(Question("R1-05", 1, "Through which managers are we exposed to Calder Packaging?", "set", frozenset(mgrs)))
    add(Question("R1-06", 1, "Did we know Calder Packaging was in trouble? When did we first learn of a write-down?",
                 "date", T.first_learnt(w, C), note="A low-confidence concern on 28 July waits for review"))
    add(Question("R1-07", 1, "And excluding co-investments?", "number", T.exposure(w, C, D, {"coinvest"}),
                 routes=route_sigs(w, C, D, kinds_out=("coinvest",)), traps=("follow_up",), follows="R1-01"))
    d5 = dt.date(2026, 9, 5)
    add(Question("R1-08", 1, "How exposed were we to Calder Packaging as of 5 September 2026?", "number",
                 T.exposure(w, C, d5), routes=route_sigs(w, C, d5), traps=("point_in_time",)))
    eu = T.sector_exposure(w, "Packaging", D, region="europe")
    add(Question("R1-09", 1, "What is our exposure to European packaging companies?", "number", eu))
    add(Question("R1-10", 1, "And excluding Calder Packaging?", "number",
                 T.sector_exposure(w, "Packaging", D, region="europe", exclude_companies={C}), traps=("follow_up",),
                 follows="R1-09"))
    add(Question("R1-11", 1, "How much of our Calder Packaging exposure comes through funds of funds?", "number",
                 sum(r.value for r in T.exposure_routes(w, C, D) if r.kind == "fof"), routes=route_sigs(w, C, D, only=("fof",))))
    d9 = dt.date(2026, 9, 9)
    add(Question("R1-12", 1, "What was our exposure to Calder Packaging on 9 September 2026, before the write-down letter arrived?",
                 "number", T.exposure(w, C, d9), routes=route_sigs(w, C, d9), traps=("point_in_time",)))
    funds = {w.funds[r.vehicles[-1]].name for r in T.exposure_routes(w, C, D) if r.vehicles[-1] in w.funds}
    add(Question("R1-13", 1, "Which of our funds hold Calder Packaging?", "set", frozenset(funds)))
    add(Question("R1-14", 1, "What fees do we pay on the Calderwick Holdings co-investment?", "refusal", "role",
                 traps=("role",)))
    add(Question("R1-15", 1, "News says Calder Packaging has $400m of debt. What is our share of that debt?", "refusal",
                 "news", traps=("news",)))
    add(Question("R1-16", 1, "How exposed are we to Sabrel Security?", "number", T.exposure(w, "C0006", D),
                 routes=route_sigs(w, "C0006", D)))
    add(Question("R1-17", 1, "What is our exposure to Nordvale Logistics?", "number", T.exposure(w, "C0007", D),
                 traps=("exit",), note="Sold: sale agreed 12 August, learnt 19 August"))
    add(Question("R1-18", 1, "What are our top 5 companies by look-through exposure?", "set",
                 frozenset(name(w, c) for c in T.top_companies(w, D, 5))))
    add(Question("R1-19", 1, "What share of our total portfolio value is Calder Packaging?", "number",
                 100 * exp / T.total_nav(w, D)))
    add(Question("R1-20", 1, "What is our exposure to packaging companies in the United Kingdom?", "number",
                 T.sector_exposure(w, "Packaging", D, country="United Kingdom")))

    # ---------------- Request 2: the committee pack, as of 30 September 2026, dashboard
    def table(fn, pids, d=P):
        return {w.funds[w.positions[p].vehicle_id].name: fn(w, p, d) for p in pids}

    add(Question("R2-01", 2, "How are our 2019 to 2021 buyout funds doing against plan, after fees?", "table",
                 table(T.tvpi_vs_plan, b19), tol=0.01))
    add(Question("R2-02", 2, "What is the net IRR of each of our 2019 to 2021 buyout funds?", "table",
                 table(T.net_irr, b19), tol=0.002))
    ptv = T.pooled(w, b19, P, "tvpi")
    add(Question("R2-03", 2, "What is the pooled net TVPI of our 2019-2021 buyout funds?", "number", ptv))
    add(Question("R2-04", 2, "What is the pooled DPI of our 2019-2021 buyout funds?", "number", T.pooled(w, b19, P, "dpi")))
    add(Question("R2-05", 2, "How much unfunded commitment do we have in our 2019-2021 buyout funds?", "number",
                 sum(T.unfunded(w, p, P, 2) for p in b19)))
    add(Question("R2-06", 2, "How much of our unfunded commitment will be called in the next 12 months?", "number",
                 sum(T.calls_next_12m(w, p, P) for p in allf)))
    add(Question("R2-07", 2, "How much will our 2019 to 2021 buyout funds call in the next 12 months?", "number",
                 sum(T.calls_next_12m(w, p, P) for p in b19)))
    behind = {w.funds[w.positions[p].vehicle_id].name for p in b19 if T.tvpi_vs_plan(w, p, P) < 0}
    add(Question("R2-08", 2, "Which of our 2019-2021 buyout funds are behind plan?", "set", frozenset(behind)))
    add(Question("R2-09", 2, "What is our total unfunded commitment across the portfolio?", "number",
                 sum(T.unfunded(w, p, P, 2) for p in allf)))
    add(Question("R2-10", 2, "What is the net IRR of Halvane Capital Partners V?", "number", T.net_irr(w, hv_pid, P),
                 tol=0.01))
    add(Question("R2-11", 2, "After fees, what multiple of our money have the 2019 to 2021 buyout funds returned so far?",
                 "number", ptv, traps=("rephrase",)))
    add(Question("R2-12", 2, "Pooled net TVPI for 2019-2021 buyouts as of 30 September 2026, please rerun.", "number", ptv,
                 traps=("rephrase",)))
    j30 = dt.date(2026, 6, 30)
    add(Question("R2-13", 2, "What was the pooled net TVPI of our 2019-2021 buyout funds as of 30 June 2026?", "number",
                 T.pooled(w, T.our_funds(w, j30, "buyout", (2019, 2021)), j30, "tvpi"), traps=("point_in_time",)))
    add(Question("R2-14", 2, "Did any metric definition change since last quarter's pack?", "set", frozenset({"unfunded"})))
    add(Question("R2-15", 2, "What is the PME of our 2019-2021 buyout funds against the MSCI World?", "refusal",
                 "no_definition", traps=("no_definition",)))
    q3s, q3e = dt.date(2026, 7, 1), dt.date(2026, 9, 30)
    add(Question("R2-16", 2, "How much did our 2019-2021 buyout funds distribute to us in the third quarter of 2026?",
                 "number", sum(T.distributions(w, p, q3e, q3s) for p in b19)))
    add(Question("R2-17", 2, "How much capital was called from us across the portfolio in the third quarter of 2026?",
                 "number", sum(T.calls_between(w, p, q3s, q3e) for p in T.our_funds(w, q3e))))
    add(Question("R2-18", 2, "What is the unfunded commitment of our 2019-2021 buyout funds using last quarter's pack definition?",
                 "number", sum(T.unfunded(w, p, P, 1) for p in b19), traps=("version",)))
    add(Question("R2-19", 2, "What is the gross IRR of our 2019-2021 buyout funds?", "refusal", "no_definition",
                 traps=("no_definition",)))
    add(Question("R2-20", 2, "How much will Halvane Capital Partners V call in the next 12 months?", "number",
                 T.calls_next_12m(w, hv_pid, P)))

    # ---------------- Request 3: a relationship decision (Brennick), briefing note
    issues = frozenset(f"LET:{x}" for x in T.manager_issues(w, "M02", D))
    commit = sum(w.positions[p].commitment for p in bre)
    bfunds = frozenset(w.funds[w.positions[p].vehicle_id].name for p in bre)
    add(Question("R3-01", 3, "Brennick Capital Partners is raising Fund VI. What is our history with them?", "composite",
                 dict(commitment=commit, funds=bfunds, issues=issues)))
    add(Question("R3-02", 3, "How much have we committed to Brennick funds in total?", "number", commit))
    add(Question("R3-03", 3, "What is the net TVPI of each Brennick fund we are in?", "table", table(T.tvpi, bre), tol=0.01))
    b4 = f"P{w.planted['brennick_funds'][1]}"
    add(Question("R3-04", 3, "What is the net IRR of Brennick Capital Partners IV?", "number", T.net_irr(w, b4, P), tol=0.01))
    add(Question("R3-05", 3, "What issues has Brennick raised in its letters?", "set", issues))
    team = frozenset(f"LET:{e.letter_id}" for e in w.events.values() if e.manager_id == "M02" and e.kind == "team_change")
    add(Question("R3-06", 3, "Has Brennick had any key person or team changes?", "set", team))
    cos = frozenset(w.companies[c.company_id].name.replace(" Inc.", "") for c in w.coinvests.values()
                    if w.funds[c.alongside_fund_id].manager_id == "M02")
    add(Question("R3-07", 3, "What co-investments have we made with Brennick?", "set", cos))
    add(Question("R3-08", 3, "What fees do we pay on our Brennick co-investments?", "refusal", "role", traps=("role",)))
    fees = {w.companies[c.company_id].name.replace(" Inc.", ""): c.mgmt_fee_pct for c in w.coinvests.values()
            if w.funds[c.alongside_fund_id].manager_id == "M02"}
    add(Question("R3-09", 3, "What fees do we pay on our Brennick co-investments?", "table", fees, role="head_of_pe",
                 tol=0.001, note="Same question, asked by the head of private equity"))
    add(Question("R3-10", 3, "How much are we planning to commit to Brennick Capital Partners VI?", "refusal", "role",
                 traps=("role",)))
    moves = T.former_partner_destinations(w, "M02")
    mara = {w.managers[j[0]].name for p in w.people.values() if p.name == "Mara Ellingsby" for j in p.jobs if j[0] != "M02"}
    add(Question("R3-11", 3, "Where did Mara Ellingsby go after leaving Brennick?", "set", frozenset(mara)))
    add(Question("R3-12", 3, "Which of our other managers employ former Brennick partners?", "set",
                 frozenset(w.managers[m].name for m in moves)))
    add(Question("R3-13", 3, "How much have Brennick funds distributed to us in total?", "number",
                 sum(T.distributions(w, p, P) for p in bre)))
    add(Question("R3-14", 3, "What is our pooled net TVPI across Brennick funds?", "number", T.pooled(w, bre, P, "tvpi")))
    rest = frozenset(f"LET:{e.letter_id}" for e in w.events.values() if e.manager_id == "M02" and e.kind == "restatement")
    add(Question("R3-15", 3, "Was a Brennick fund valuation ever restated?", "set", rest))
    b3 = f"P{w.planted['brennick_funds'][0]}"
    add(Question("R3-16", 3, "What is the DPI of Brennick Capital Partners III?", "number", T.dpi(w, b3, P)))
    add(Question("R3-17", 3, "How much unfunded commitment do we have to Brennick funds?", "number",
                 sum(T.unfunded(w, p, P, 2) for p in bre)))
    d23 = dt.date(2023, 12, 31)
    add(Question("R3-18", 3, "What issues had Brennick raised in its letters as of 31 December 2023?", "set",
                 frozenset(f"LET:{x}" for x in T.manager_issues(w, "M02", d23)), traps=("point_in_time",)))
    add(Question("R3-19", 3, "How much are our Brennick funds worth today?", "number",
                 sum(T.adjusted_nav(w, p, D) for p in T.our_funds(w, D, manager_id="M02"))))
    add(Question("R3-20", 3, "Should we invest in Brennick Capital Partners VI?", "refusal", "advice", traps=("advice",)))
    assert len(qs) == 60
    return qs
