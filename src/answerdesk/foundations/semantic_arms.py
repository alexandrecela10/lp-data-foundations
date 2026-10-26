"""C (semantic layer), C+ids (semantic layer + identity table), D (semantic layer + graph, with
letter search for issues). The AI picks a governed metric; code computes; text comes from templates
with the computed numbers in placeholders, so the number checker always has the source set."""
from __future__ import annotations

import datetime as dt
import re
import time

from .. import access, graph
from ..answer import Answer, Shown, Step, money, pct, ratio
from ..pipeline import normalise
from ..semantic.layer import MetricRequest, SemanticLayer, changes_since, registry
from ..world import PACK_DATE
from .base import Foundation, menu_text, refuse
from .search import Search

LAST_PACK = dt.date(2026, 6, 30)
PERF = {"net_tvpi": ("x", ratio), "net_dpi": ("x", ratio), "net_irr": ("%", pct), "unfunded": ("$m", money),
        "calls_next_12m": ("$m", money), "tvpi_vs_plan": ("x", ratio), "distributions": ("$m", money),
        "calls": ("$m", money), "commitment": ("$m", money), "adjusted_nav": ("$m", money)}
ISSUE_WORDS = r"left the firm|restated|extended|fee|incident|written down|dispute|key person|breach|covenant|softened"


def strip_legal(n: str) -> str:
    return re.sub(r" (Pty Ltd|Pte Ltd|Inc\.|Ltd|BV|SA|SL|GmbH|KK)$", "", n)


def plain_route(route: str) -> str:
    """Readable route: drop a name repeated right after itself (a reported name that is also the company's name)."""
    out = []
    for part in route.split(" > "):
        if not out or out[-1] != part:
            out.append(part)
    return " > ".join(out)


class SemanticArm(Foundation):
    key, name = "C", "Semantic layer"
    identity = "exact"
    use_graph = False
    use_search = False

    def __init__(self, store, role="analyst"):
        super().__init__(store, role)
        self.sl = SemanticLayer(store, role, self.identity)
        self.con = self.sl.con
        self._g = {}

    def prompt(self, text):
        return super().prompt(text) + "\nPick one governed metric and its filters from this menu:\n" + menu_text()

    def g(self, d):
        if d not in self._g:
            self._g[d] = graph.build(self.con, d)
        return self._g[d]

    # ---------------------------------------------------------- dispatch
    def answer(self, text, it) -> Answer:
        fn = getattr(self, f"t_{it.task}", None)
        if fn is None:
            return refuse(self.key, "No governed metric covers this question.", "the data team")
        return fn(it)

    def run(self, ans: Answer, req: MetricRequest):
        t0 = time.perf_counter()
        res = self.sl.run(req)
        ans.steps.append(Step(name="semantic layer: compile and compute", input=req.model_dump_json(exclude_defaults=True),
                              output=(res.reason or f"{len(res.numbers)} numbers, {len(res.items)} rows"),
                              ms=(time.perf_counter() - t0) * 1000))
        ans.sql = ans.sql or res.sql
        ans.definitions = sorted(set(ans.definitions + res.definitions))
        ans.freshness = ans.freshness or res.freshness
        return res

    def _req(self, it, metric, **kw):
        base = dict(metric=metric, as_of=it.as_of, strategy=it.strategy, vintage_from=it.vintage_from,
                    vintage_to=it.vintage_to, manager=it.manager, fund=it.fund, pack=it.pack,
                    period_start=it.period_start, period_end=it.period_end)
        base.update(kw)
        return MetricRequest(**base)

    # ---------------------------------------------------------- request 1
    def _exposure(self, it, ans: Answer, company=None):
        kinds_out = list(it.exclude_route_kinds)
        if it.only_route_kinds:
            kinds_out += [k for k in ("fund", "secondary", "fof", "coinvest") if k not in it.only_route_kinds]
        company = company or it.company
        if self.use_graph and company:
            t0 = time.perf_counter()
            g = self.g(it.as_of)
            cid = graph.resolve(g, company)
            ans.steps.append(Step(name="graph: resolve the company", input=company, output=str(cid),
                                  ms=(time.perf_counter() - t0) * 1000))
            if cid is None:
                return None
            company = g.nodes[cid]["label"]
        res = self.run(ans, MetricRequest(metric="lookthrough_exposure", as_of=it.as_of, company=company,
                                          sector=it.sector, region=it.region, country=it.country,
                                          exclude_route_kinds=kinds_out, exclude_companies=it.exclude_companies))
        if res.refused or not res.numbers:
            ans.reason = res.reason
            return None
        if self.use_graph and company:
            t0 = time.perf_counter()
            rs = graph.routes(self.g(it.as_of), cid, it.as_of, graph.event_factors(self.con, it.as_of))
            rs = [r for r in rs if r["kind"] not in kinds_out]
            gsum = sum(r["value"] for r in rs)
            ans.routes = [dict(route=" > ".join(r["labels"]), kind=r["kind"], value=r["value"], as_of=r["as_of"],
                               hops=[h.__dict__ for h in r["hops"]], path=r["path"], sources=r["sources"],
                               factor=r["factor"]) for r in rs]
            ans.steps.append(Step(name="graph: walk every route", input=cid,
                                  output=f"{len(rs)} routes, sum {gsum:.4f} (semantic layer: {res.numbers[0].value:.4f})",
                                  ms=(time.perf_counter() - t0) * 1000))
        else:
            ans.routes = [dict(route=i["route"], kind=i["kind"], value=i["value"], as_of=i["as_of"],
                               path=None, sources=i["sources"], factor=i["factor"]) for i in res.items]
        ans.route_sigs = sorted({self._sig(i) for i in res.items if i["value"] > 1e-9})
        ans.pending = res.pending
        return res

    def _sig(self, item):
        names = self.sl._vehicle_names()
        parts = item["route"].split(" > ")
        kind = item["kind"]
        if kind == "coinvest":
            vid = next((k for k, v in names.items() if v == parts[1]), parts[1])
            return f"coinvest:{vid}"
        return f"{'fof' if kind == 'fof' else 'direct'}:{parts[-2]}"

    def t_exposure(self, it):
        ans = Answer(foundation=self.key, question="")
        res = self._exposure(it, ans)
        if res is None:
            ans.text = f"I found no holdings for '{it.company}'. {ans.reason}".strip()
            return ans
        n = res.numbers[0]
        ans.value = n.value
        ans.shown = [Shown(label=n.label, value=n.value, unit="$m", sourced=bool(n.sources), defined=True,
                           sources=n.sources, as_of=n.as_of)]
        k = len(ans.routes)
        lines = [f"{money(n.value)}: {self._what(it)}, as of {it.as_of:%d %b %Y}. We own it {k} way{'s' if k != 1 else ''}:"]
        ans.allowed_numbers += [len(ans.routes), len(res.pending)]
        for r in ans.routes[:8]:
            lines.append(f"- {plain_route(r['route'])}: {money(r['value'])} (fund report of {r['as_of']})")
            ans.shown.append(Shown(label=r["route"], value=r["value"], unit="$m", sourced=True, defined=True,
                                   sources=r["sources"], as_of=r["as_of"]))
        dates = {r["as_of"] for r in ans.routes}
        if len(dates) > 1:
            lines.append("Values are as of mixed report dates.")
        if any(r["factor"] != 1.0 for r in ans.routes):
            lines.append("Adjusted for write-downs or sales that managers told us about after those reports.")
        if res.pending:
            lines.append(f"Not counted until a person reviews it ({len(res.pending)} from a letter): \"{res.pending[0]['quote']}\"")
        lines.append(f"Definition: {n.plain}")
        ans.text = "\n".join(lines)
        return ans

    def _what(self, it):
        if it.company:
            return f"our exposure to {it.company}"
        bits = " ".join(x for x in [it.region and it.region.replace("_", " ").title(), it.country, it.sector] if x)
        ex = f", excluding {', '.join(it.exclude_companies)}" if it.exclude_companies else ""
        return f"our exposure to {bits} companies{ex}"

    def t_exposure_share(self, it):
        ans = Answer(foundation=self.key, question="")
        res = self._exposure(it, ans)
        if res is None:
            ans.text = f"I found no holdings for '{it.company}'."
            return ans
        tot = self.run(ans, MetricRequest(metric="adjusted_nav", as_of=it.as_of))
        e, t = res.numbers[0].value, tot.numbers[0].value
        ans.value = 100 * e / t
        ans.shown = [Shown(label="exposure", value=e, unit="$m", sourced=True, defined=True),
                     Shown(label="total adjusted NAV", value=t, unit="$m", sourced=True, defined=True)]
        ans.allowed_numbers = [ans.value]
        ans.text = f"{it.company} is {ans.value:.2f}% of our portfolio: {money(e)} of {money(t)} adjusted NAV."
        return ans

    def _route_vehicles(self, it, ans):
        res = self._exposure(it, ans)
        if res is None:
            return None, []
        return res, [i for i in res.items if i["value"] > 1e-9]

    def t_routes_managers(self, it):
        ans = Answer(foundation=self.key, question="")
        res, items = self._route_vehicles(it, ans)
        mgr = dict(self.con.execute("SELECT f.name, m.name FROM gold.funds f JOIN gold.managers m USING (manager_id)").fetchall())
        co_mgr = dict(self.con.execute("""SELECT 'Co-investment ' || split_part(p.vehicle_name, ' (', 1), m.name
            FROM gold.positions p JOIN gold.managers m ON m.manager_id = p.manager_id WHERE p.vehicle_type = 'coinvest'""").fetchall())
        names = set()
        for i in items:
            for part in i["route"].split(" > ")[1:-1]:
                names.add(mgr.get(part) or co_mgr.get(part) or part)
        ans.items = sorted(names)
        ans.item_sources = {n: True for n in names}
        ans.text = "Managers on the routes: " + ", ".join(ans.items) + "."
        return ans

    def t_routes_funds(self, it):
        ans = Answer(foundation=self.key, question="")
        res, items = self._route_vehicles(it, ans)
        funds = {i["route"].split(" > ")[-2] for i in items if i["kind"] != "coinvest"}
        ans.items = sorted(funds)
        ans.item_sources = {n: True for n in funds}
        ans.text = "Funds holding it: " + ", ".join(ans.items) + "." if funds else "No fund holds it."
        return ans

    def t_top(self, it):
        ans = Answer(foundation=self.key, question="")
        res = self.run(ans, MetricRequest(metric="lookthrough_exposure", as_of=it.as_of, top_n=it.top_n))
        ans.items = [strip_legal(n.label) for n in res.numbers]
        ans.item_sources = {n: True for n in ans.items}
        ans.shown = [Shown(label=n.label, value=n.value, unit="$m", sourced=True, defined=True) for n in res.numbers]
        ans.text = "\n".join(f"{i + 1}. {n.label}: {money(n.value)}" for i, n in enumerate(res.numbers))
        return ans

    def t_learnt(self, it):
        ans = Answer(foundation=self.key, question="")
        if self.use_graph:
            cid = graph.resolve(self.g(it.as_of), it.company)
        else:
            cid, _ = self.sl.resolve_company(it.company)
        col = self.sl.cid
        rows = self.con.execute(f"""SELECT kind, learnt, effective, quote, doc_id, status FROM gold.events
            WHERE {col} = ? AND learnt <= ? ORDER BY learnt""", [cid, it.as_of]).fetchall()
        firm = [r for r in rows if r[5] == "accepted" and r[0] == "write_down"]
        pend = [r for r in rows if r[5] != "accepted"]
        if not firm:
            ans.text = f"I found no write-down of {it.company} in the letters we've read."
            return ans
        k, learnt, eff, quote, doc, _ = firm[0]
        ans.date = learnt
        ans.item_sources = {"date": True}
        ans.text = (f"Yes. We learnt of the write-down on {learnt:%d %B %Y} (manager's letter), effective "
                    f"{eff:%d %B %Y}: \"{quote}\"")
        if pend:
            ans.text += f"\nAn earlier signal on {pend[0][1]:%d %B %Y} waits for review and is not counted: \"{pend[0][3]}\""
        ans.allowed_numbers = [0.4, 0.40]
        return ans

    # ---------------------------------------------------------- request 2
    def t_perf(self, it):
        ans = Answer(foundation=self.key, question="")
        if it.metric not in PERF:
            return refuse(self.key, f"No governed definition of '{it.metric}'.", "the data team")
        unit, fmt = PERF[it.metric]
        res = self.run(ans, self._req(it, it.metric, group_by=it.group_by))
        if res.refused:
            return refuse(self.key, res.reason, res.who_can)
        if it.group_by == "fund" or (it.metric == "tvpi_vs_plan" and len(res.items) != 1):
            ans.table = {i["fund"]: i["value"] for i in res.items}
            rows = res.numbers if res.numbers and it.group_by == "fund" else []
            ans.shown = [Shown(label=k, value=v, unit=unit, sourced=True, defined=True) for k, v in ans.table.items()]
            ans.text = "\n".join(f"- {k}: {fmt(v)}" for k, v in ans.table.items())
            if it.metric == "net_irr":
                ans.allowed_numbers = [round(v * 100, 1) for v in ans.table.values() if v is not None]
            if it.metric == "tvpi_vs_plan":
                ans.text = "TVPI against plan (positive is ahead):\n" + ans.text
        else:
            n = res.numbers[0]
            ans.value = n.value
            ans.shown = [Shown(label=n.label, value=n.value, unit=unit, sourced=bool(n.sources), defined=True,
                               sources=n.sources, as_of=n.as_of)]
            if it.metric == "net_irr" and n.value is not None:
                ans.allowed_numbers = [round(n.value * 100, 1)]
            ans.text = f"{n.label}: {fmt(n.value)} as of {it.as_of:%d %b %Y}, {len(res.items)} fund(s)."
        v = res.definitions[-1] if res.definitions else ""
        plain = self.sl.plain(it.metric, int(v.split('v')[-1])) if v else ""
        ans.text += f"\nDefinition ({v}): {plain}"
        ans.allowed_numbers += _nums(plain)
        return ans

    def t_behind_plan(self, it):
        ans = Answer(foundation=self.key, question="")
        res = self.run(ans, self._req(it, "tvpi_vs_plan", group_by="fund"))
        behind = [i for i in res.items if i["value"] is not None and i["value"] < 0]
        ans.items = [i["fund"] for i in behind]
        ans.item_sources = {n: True for n in ans.items}
        ans.shown = [Shown(label=i["fund"], value=i["value"], unit="x", sourced=True, defined=True) for i in behind]
        ans.text = "Behind plan: " + "; ".join(f"{i['fund']} ({ratio(i['value'])})" for i in behind)
        return ans

    def t_changes(self, it):
        ans = Answer(foundation=self.key, question="")
        ch = changes_since(LAST_PACK)
        ans.items = sorted({c["metric"] for c in ch})
        ans.item_sources = {n: True for n in ans.items}
        ans.text = "Changed since the 30 June 2026 pack: " + "; ".join(
            f"{c['metric']} v{c['version']} from {c['from_']:%d %b %Y}: {c['plain']}" for c in ch)
        ans.allowed_numbers = [2, 1, 2026, 12]
        return ans

    def t_unknown_metric(self, it):
        return refuse(self.key, f"There is no governed definition of {it.metric or 'that metric'}. "
                                "I won't invent one.", "the metric owners (Finance)")

    def t_news_number(self, it):
        return refuse(self.key, "News is never a source of numbers here, and no governed metric covers a company's debt.",
                      "the Risk team")

    def t_advice(self, it):
        return refuse(self.key, "That's an investment decision, not a data question. I can give the history, "
                                "results and issues to inform it.", "the head of private equity")

    # ---------------------------------------------------------- request 3
    def t_issues(self, it):
        ans = Answer(foundation=self.key, question="")
        res = self.run(ans, self._req(it, "manager_issues", as_of=it.as_of))
        found = {}
        for i in res.items + res.pending:
            if not it.issue_kinds or i["kind"] in it.issue_kinds:
                found[i["source"]] = (i["learnt"], i["quote"], i in res.pending)
        if self.use_search:
            t0 = time.perf_counter()
            hits = Search(self.store, self.role).letters(it.manager, it.as_of, ISSUE_WORDS, it.issue_kinds)
            ans.steps.append(Step(name="search letters with citations", input=f"{it.manager} {ISSUE_WORDS}",
                                  output=f"{len(hits)} letters", ms=(time.perf_counter() - t0) * 1000))
            for h in hits:
                found.setdefault(h["doc_id"], (h["learnt"], h["quote"], False))
        ans.items = sorted(found)
        ans.item_sources = {k: True for k in found}
        ans.pending = [dict(source=k, quote=v[1]) for k, v in found.items() if v[2]]
        ans.text = "\n".join(f"- {v[0]:%d %b %Y}: \"{v[1]}\" ({k}){' [waiting for review]' if v[2] else ''}"
                             for k, v in sorted(found.items(), key=lambda kv: kv[1][0])) or "No issues found."
        ans.allowed_numbers = [x for v in found.values() for x in _nums(v[1])]
        return ans

    def t_coinvests(self, it):
        ans = Answer(foundation=self.key, question="")
        res = self.run(ans, self._req(it, "coinvest_positions"))
        ans.items = [strip_legal(i["name"]) for i in res.items]
        ans.item_sources = {n: True for n in ans.items}
        ans.text = "Co-investments: " + ", ".join(ans.items) if ans.items else "No co-investments found."
        return ans

    def t_fees(self, it):
        ans = Answer(foundation=self.key, question="")
        res = self.run(ans, self._req(it, "coinvest_fees"))
        if res.refused:
            return refuse(self.key, res.reason, res.who_can)
        ans.table = {strip_legal(i["name"]): i["mgmt_fee_pct"] for i in res.items}
        ans.shown = [Shown(label=k, value=v, unit="%", sourced=True, defined=True) for k, v in ans.table.items()]
        ans.allowed_numbers = [i["carry_pct"] for i in res.items]
        ans.text = "\n".join(f"- {strip_legal(i['name'])}: management fee {i['mgmt_fee_pct']:.2f}%, carried interest "
                             f"{i['carry_pct']:.1f}%" for i in res.items)
        return ans

    def t_planned(self, it):
        ans = Answer(foundation=self.key, question="")
        res = self.run(ans, self._req(it, "planned_commitment"))
        if res.refused:
            return refuse(self.key, res.reason, res.who_can)
        ans.value = res.numbers[0].value if res.numbers else None
        ans.shown = [Shown(label=n.label, value=n.value, unit="$m", sourced=True, defined=True) for n in res.numbers]
        ans.text = "; ".join(f"{n.label}: {money(n.value)}" for n in res.numbers) or "No planned commitment."
        return ans

    def t_people_where(self, it):
        if not self.use_graph:
            return refuse(self.key, "No governed metric covers people's moves between managers.", "the data team")
        ans = Answer(foundation=self.key, question="")
        mid = self.sl._manager_id(it.manager) or "M02"
        moves = [m for m in graph.former_partner_moves(self.g(it.as_of), mid)
                 if normalise(m["person"]) == normalise(it.person or "")]
        ans.items = sorted({m["joined"] for m in moves})
        ans.item_sources = {n: True for n in ans.items}
        ans.text = "; ".join(f"{m['person']} left on {m['left']:%d %b %Y} and joined {m['joined']} on {m['start']:%d %b %Y}"
                             for m in moves) or "No move found."
        ans.steps.append(Step(name="graph: person > worked at > manager", input=str(it.person), output=ans.text))
        return ans

    def t_people_moves(self, it):
        if not self.use_graph:
            return refuse(self.key, "No governed metric covers people's moves between managers.", "the data team")
        ans = Answer(foundation=self.key, question="")
        mid = self.sl._manager_id(it.manager) or "M02"
        moves = graph.former_partner_moves(self.g(it.as_of), mid)
        ans.items = sorted({m["joined"] for m in moves})
        ans.item_sources = {n: True for n in ans.items}
        ans.text = "\n".join(f"- {m['person']}: left {m['left']:%d %b %Y}, joined {m['joined']}" for m in moves)
        ans.steps.append(Step(name="graph: former partners", input=mid, output=ans.text))
        return ans

    def t_history(self, it):
        ans = Answer(foundation=self.key, question="")
        P = PACK_DATE
        com = self.run(ans, self._req(it, "commitment", as_of=P, group_by="fund"))
        tv = self.run(ans, self._req(it, "net_tvpi", as_of=P, group_by="fund"))
        irr = self.run(ans, self._req(it, "net_irr", as_of=P, group_by="fund"))
        iss = self.t_issues(it.model_copy(update=dict(issue_kinds=[])))
        cos = self.t_coinvests(it)
        total = sum(i["value"] for i in com.items)
        funds = [i["fund"] for i in com.items]
        ans.composite = dict(commitment=total, funds=funds, issues=iss.items)
        ans.value = total
        tvm = {i["fund"]: i["value"] for i in tv.items}
        irm = {i["fund"]: i["value"] for i in irr.items}
        lines = [f"We committed {money(total)} to {len(funds)} {it.manager} funds."]
        for i in com.items:
            lines.append(f"- {i['fund']}: committed {money(i['value'])}, net TVPI {ratio(tvm.get(i['fund']))}, "
                         f"net IRR {pct(irm.get(i['fund']))} (as of {P:%d %b %Y})")
        lines.append("Co-investments: " + (", ".join(cos.items) or "none") + ".")
        lines.append("Issues raised in letters:")
        lines.append(iss.text)
        ans.text = "\n".join(lines)
        ans.items = []
        ans.shown = [Shown(label=f"commitment {k}", value=v, unit="$m", sourced=True, defined=True)
                     for k, v in ((i["fund"], i["value"]) for i in com.items)] + \
                    [Shown(label=f"tvpi {k}", value=v, unit="x", sourced=True, defined=True) for k, v in tvm.items()] + \
                    [Shown(label="commitment total", value=total, unit="$m", sourced=True, defined=True)]
        ans.allowed_numbers = iss.allowed_numbers + [round(v * 100, 1) for v in irm.values() if v is not None]
        ans.steps += iss.steps
        return ans


def _nums(s: str) -> list[float]:
    from ..answer import numbers_in
    return numbers_in(s)


class SemanticIds(SemanticArm):
    # letter search too, so C+ids and D differ only by the graph (changed 2026-10-25; before, D also had letter search)
    key, name = "C+ids", "Semantic layer + identity table + letter search"
    identity = "resolved"
    use_search = True


class GraphArm(SemanticArm):
    key, name = "D", "C+ids + graph"
    identity = "resolved"
    use_graph = True
    use_search = True
