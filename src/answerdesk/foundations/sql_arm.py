"""B: warehouse tables + AI-written SQL.

The AI sees curated views with column notes (below) and writes SQL; code runs it read-only on the
role's copy of the warehouse. The warehouse is what most LPs have: names as reported, an exact-name
company key and parent links. It has no identity matching and no metric definitions.

OFFLINE STAND-IN. Offline, the SQL is written by templates that do what a competent writer would do
from the column notes alone: join positions to the latest reports and holdings, one level of fund of
funds, co-investments, parent companies; ILIKE on the name asked. What the notes don't say, the
templates don't do: dedupe a fund of funds' copy of a report, filter on when a report arrived,
apply write-downs from letters, roll NAV forward, use the governed call forecast. Live mode replaces
the templates with Claude writing SQL from the same notes.
"""
from __future__ import annotations

import datetime as dt
import re
import time

import duckdb

from .. import access
from ..answer import Answer, Shown, Step, money, pct, ratio
from .base import Foundation, refuse

NOTES = {
    "positions": "one row per holding: vehicle_id (fund, fund of funds or co-investment id), vehicle_type, acquired (primary or secondary), commitment ($m), start_date, purchase_price, plan_tvpi (target multiple), manager_id",
    "reports": "fund quarterly reports: fund_id, as_of (quarter end), learnt (date received), fund_nav ($m), lp_share (our ownership, 0-1), lp_nav (our value, $m), reported_irr and reported_tvpi (the manager's own figures)",
    "holdings": "companies in each fund report: fund_id, as_of, learnt, name_reported (as the manager spells it), company_key, company_id_exact (exact-name match to companies), value ($m, in the fund), via (own report, or fof_copy inside a fund of funds report)",
    "fof_stakes": "fund of funds holdings: fof_id, fund_id, share (0-1), as_of, learnt",
    "coinvest_values": "co-investment statements: coinvest_id, name_reported, as_of, learnt, value ($m, ours)",
    "cashflows": "our cash flows: position_id, kind (call, dist, purchase), amount ($m), recallable, notice_date, value_date",
    "companies": "reference: company_id, name, sector, country, region, parent_id, is_holdco",
    "funds": "reference: fund_id, manager_id, name, vintage, strategy, size",
    "managers": "reference: manager_id, name, strategy, region",
    "people": "manager partners: person_id, name, manager_id, start_date, end_date, title",
    "events": "events read from manager letters: kind, company_name, factor, effective, learnt, status, quote, doc_id, manager_id",
    "letters": "manager letters: doc_id, manager_name, learnt, text",
    "coinvest_fees": "co-investment fee terms: coinvest_id, mgmt_fee_pct, carry_pct",
    "planned": "proposed commitments: manager_id, fund_name, proposed_commitment",
}
DROP = {"holdings": ["company_id", "match_method"], "coinvest_values": ["company_id"], "events": ["company_id"]}
_cache: dict = {}


def warehouse(store, role) -> duckdb.DuckDBPyConnection:
    key = (id(store), role)
    if key in _cache:
        return _cache[key]
    src = access.role_db(store, role)
    con = duckdb.connect()
    con.execute("CREATE SCHEMA gold")
    for (t,) in src.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='gold'").fetchall():
        if t == "identity":
            continue
        cols = [c[0] for c in src.execute(f"DESCRIBE gold.{t}").fetchall() if c[0] not in DROP.get(t, [])]
        con.register("_t", src.execute(f"SELECT {', '.join(cols)} FROM gold.{t}").arrow())
        con.execute(f"CREATE TABLE gold.{t} AS SELECT * FROM _t")
        con.unregister("_t")
    _cache[key] = con
    return con


def schema_text(con) -> str:
    out = []
    for (t,) in con.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='gold' ORDER BY 1").fetchall():
        out.append(f"gold.{t}: {NOTES.get(t, '')}")
    return "\n".join(out)


def pattern(name: str) -> str:
    return "%" + re.sub(r"[^\w ]", "", name).strip().lower() + "%"


class SqlArm(Foundation):
    key, name = "B", "Tables + AI-written SQL"
    calls_per_answer = 2

    def __init__(self, store, role="analyst"):
        super().__init__(store, role)
        self.con = warehouse(store, role)

    def prompt(self, text):
        return super().prompt(text) + "\nWrite one DuckDB SQL query over these tables:\n" + schema_text(self.con)

    def sql(self, ans: Answer, q: str, params=None):
        t0 = time.perf_counter()
        ans.sql = (ans.sql + "\n\n" if ans.sql else "") + q.strip()
        try:
            cur = self.con.execute(q, params or {})
            cols = [c[0] for c in cur.description]
            rows = [dict(zip(cols, r)) for r in cur.fetchall()]
            ans.steps.append(Step(name="AI writes SQL; code runs it", input=q.strip()[:1500], output=f"{len(rows)} rows",
                                  ms=(time.perf_counter() - t0) * 1000))
            return rows
        except duckdb.Error as e:
            ans.steps.append(Step(name="AI writes SQL; code runs it", input=q.strip()[:1500], output=f"error: {e}"[:300],
                                  ms=(time.perf_counter() - t0) * 1000))
            raise

    def answer(self, text, it) -> Answer:
        if self.live:
            try:
                return self.live_answer(text, it)
            except Exception:
                pass
        fn = getattr(self, f"t_{it.task}", None)
        if fn is None:
            return refuse(self.key, "I couldn't write a query for this from the tables I have.")
        try:
            return fn(it)
        except duckdb.Error as e:
            msg = str(e).split("\n")[0]
            return refuse(self.key, f"The query failed ({msg[:120]}). The data may not be visible to your role.")

    def live_answer(self, text, it) -> Answer:
        from .. import llm
        ans = Answer(foundation=self.key, question="")
        data, use1 = llm.ask_json("Write one read-only DuckDB SQL query that answers the question. Tables:\n"
                                  + schema_text(self.con), f"Today is 2026-10-26. Question: {text}",
                                  llm.strict({"type": "object", "properties": {"sql": {"type": "string"}},
                                              "required": ["sql"]}))
        try:
            rows = self.sql(ans, data["sql"])[:60]
        except duckdb.Error as e:
            rows = [dict(error=str(e)[:200])]
        out, use2 = llm.ask_json("Answer from these query results only. " + llm.ANSWER_RULES,
                                 f"Question: {text}\nSQL: {data['sql']}\nRows: {rows}", llm.ANSWER_SCHEMA)
        self._usage = getattr(self, "_usage", []) + [use1, use2]
        return llm.to_answer(ans, out, sourced=False)

    # ---------------------------------------------------------- exposure SQL
    def _exposure_rows(self, it, ans, company=None):
        d = it.as_of
        where_co, params = "", {"d": d}
        if company:
            params["pat"] = pattern(company)
            names = """(SELECT name FROM gold.companies WHERE name ILIKE $pat
                        UNION SELECT p.name FROM gold.companies c JOIN gold.companies p ON p.company_id = c.parent_id
                        WHERE c.name ILIKE $pat)"""
            where_co = f"AND (h.name_reported ILIKE $pat OR h.name_reported IN {names})"
            where_cv = f"AND (c.name_reported ILIKE $pat OR c.name_reported IN {names})"
        else:
            where_cv = ""
        q = f"""
WITH lr AS (SELECT fund_id, max(as_of) AS q FROM gold.reports WHERE as_of <= $d GROUP BY fund_id),
     lh AS (SELECT fund_id, max(as_of) AS q FROM gold.holdings WHERE as_of <= $d GROUP BY fund_id),
     ls AS (SELECT fof_id, max(as_of) AS q FROM gold.fof_stakes WHERE as_of <= $d GROUP BY fof_id),
     lc AS (SELECT coinvest_id, max(as_of) AS q FROM gold.coinvest_values WHERE as_of <= $d GROUP BY coinvest_id)
SELECT 'direct' AS via, f.name AS fund, h.name_reported, h.company_id_exact, r.lp_share * h.value AS value, h.as_of
FROM gold.positions p JOIN lr ON lr.fund_id = p.vehicle_id
JOIN gold.reports r ON r.fund_id = lr.fund_id AND r.as_of = lr.q
JOIN lh ON lh.fund_id = p.vehicle_id JOIN gold.holdings h ON h.fund_id = lh.fund_id AND h.as_of = lh.q
JOIN gold.funds f ON f.fund_id = p.vehicle_id
WHERE p.vehicle_type = 'fund' {where_co}
UNION ALL
SELECT 'fof', f.name, h.name_reported, h.company_id_exact, r.lp_share * s.share * h.value, h.as_of
FROM gold.positions p JOIN lr ON lr.fund_id = p.vehicle_id
JOIN gold.reports r ON r.fund_id = lr.fund_id AND r.as_of = lr.q
JOIN ls ON ls.fof_id = p.vehicle_id JOIN gold.fof_stakes s ON s.fof_id = ls.fof_id AND s.as_of = ls.q
JOIN lh ON lh.fund_id = s.fund_id JOIN gold.holdings h ON h.fund_id = lh.fund_id AND h.as_of = lh.q
JOIN gold.funds f ON f.fund_id = s.fund_id
WHERE p.vehicle_type = 'fof' {where_co}
UNION ALL
SELECT 'coinvest', c.coinvest_id, c.name_reported, c.company_id_exact, c.value, c.as_of
FROM gold.coinvest_values c JOIN lc ON lc.coinvest_id = c.coinvest_id AND c.as_of = lc.q
WHERE TRUE {where_cv}"""
        return self.sql(ans, q, params)

    def _filter_rows(self, it, rows):
        out = [r for r in rows if r["via"] not in it.exclude_route_kinds]
        if it.only_route_kinds:
            out = [r for r in out if r["via"] in it.only_route_kinds]
        return out

    def t_exposure(self, it):
        ans = Answer(foundation=self.key, question="")
        if it.company:
            rows = self._filter_rows(it, self._exposure_rows(it, ans, it.company))
        else:
            rows = self._exposure_rows(it, ans)
            cos = {r[0]: r for r in self.con.execute("SELECT company_id, sector, region, country, name FROM gold.companies").fetchall()}
            ex = {pattern(n) for n in it.exclude_companies}

            def keep(r):
                c = cos.get(r["company_id_exact"])
                if not c or (it.sector and c[1] != it.sector) or (it.region and c[2] != it.region) or \
                        (it.country and c[3] != it.country):
                    return False
                return not any(re.fullmatch(p.replace("%", ".*"), c[4].lower()) for p in ex)
            rows = [r for r in rows if keep(r)]
        total = sum(r["value"] for r in rows)
        ans.value = total
        ans.route_sigs = sorted({f"{r['via']}:{r['fund']}" for r in rows if r["value"] > 1e-9})
        ans.routes = [dict(route=f"{r['via']} > {r['fund']} > {r['name_reported']}", kind=r["via"], value=r["value"],
                           as_of=r["as_of"]) for r in rows]
        ans.shown = [Shown(label="total", value=total, unit="$m", sourced=False)] + \
                    [Shown(label=x["route"], value=x["value"], unit="$m", sourced=False) for x in ans.routes[:8]]
        ans.text = f"Query result: {money(total)} across {len(rows)} rows.\n" + \
                   "\n".join(f"- {x['route']}: {money(x['value'])}" for x in ans.routes[:8])
        return ans

    def t_exposure_share(self, it):
        ans = self.t_exposure(it)
        nav = self.sql(ans, """WITH lr AS (SELECT fund_id, max(as_of) q FROM gold.reports WHERE as_of <= $d GROUP BY 1),
            lc AS (SELECT coinvest_id, max(as_of) q FROM gold.coinvest_values WHERE as_of <= $d GROUP BY 1)
            SELECT (SELECT sum(r.lp_nav) FROM gold.reports r JOIN lr ON lr.fund_id = r.fund_id AND lr.q = r.as_of)
                 + (SELECT sum(c.value) FROM gold.coinvest_values c JOIN lc ON lc.coinvest_id = c.coinvest_id AND lc.q = c.as_of) AS nav""",
                       {"d": it.as_of})[0]["nav"]
        share = 100 * ans.value / nav
        ans.text = f"{share:.2f}% ({money(ans.value)} of {money(nav)})."
        ans.value = share
        ans.shown += [Shown(label="share", value=share, unit="%"), Shown(label="nav", value=nav, unit="$m")]
        return ans

    def t_routes_managers(self, it):
        ans = Answer(foundation=self.key, question="")
        rows = [r for r in self._exposure_rows(it, ans, it.company) if r["value"] > 1e-9]
        fm = dict(self.con.execute("SELECT f.name, m.name FROM gold.funds f JOIN gold.managers m USING (manager_id)").fetchall())
        cm = dict(self.con.execute("""SELECT p.vehicle_id, m.name FROM gold.positions p JOIN gold.managers m ON m.manager_id = p.manager_id
            WHERE vehicle_type = 'coinvest'""").fetchall())
        names = {fm.get(r["fund"]) or cm.get(r["fund"]) for r in rows}
        if any(r["via"] == "fof" for r in rows):
            names |= {m for (m,) in self.con.execute("""SELECT m.name FROM gold.positions p JOIN gold.funds f ON f.fund_id = p.vehicle_id
                JOIN gold.managers m ON m.manager_id = f.manager_id WHERE p.vehicle_type = 'fof'""").fetchall()}
        ans.items = sorted(n for n in names if n)
        ans.text = "Managers: " + ", ".join(ans.items)
        return ans

    def t_routes_funds(self, it):
        ans = Answer(foundation=self.key, question="")
        rows = [r for r in self._exposure_rows(it, ans, it.company) if r["value"] > 1e-9 and r["via"] != "coinvest"]
        ans.items = sorted({r["fund"] for r in rows})
        ans.text = "Funds: " + ", ".join(ans.items)
        return ans

    def t_top(self, it):
        ans = Answer(foundation=self.key, question="")
        rows = self._exposure_rows(it, ans)
        agg = {}
        names = dict(self.con.execute("SELECT company_id, name FROM gold.companies").fetchall())
        for r in rows:
            k = names.get(r["company_id_exact"], r["name_reported"])
            agg[k] = agg.get(k, 0) + r["value"]
        top = sorted(agg.items(), key=lambda kv: -kv[1])[: it.top_n or 5]
        ans.items = [re.sub(r" (Pty Ltd|Pte Ltd|Inc\.|Ltd|BV|SA|SL|GmbH|KK)$", "", k) for k, _ in top]
        ans.shown = [Shown(label=k, value=v, unit="$m") for k, v in top]
        ans.text = "\n".join(f"{i + 1}. {k}: {money(v)}" for i, (k, v) in enumerate(top))
        return ans

    def t_learnt(self, it):
        ans = Answer(foundation=self.key, question="")
        rows = self.sql(ans, """SELECT min(learnt) AS first FROM gold.events WHERE kind = 'write_down' AND company_name ILIKE $pat""",
                        {"pat": pattern(it.company or "")})
        ans.date = rows[0]["first"]
        ans.text = f"First write-down learnt on {ans.date}." if ans.date else "No write-down found."
        return ans

    # ---------------------------------------------------------- performance SQL
    def _scope_sql(self, it):
        conds = ["p.vehicle_type IN ('fund','fof')"]
        if it.strategy or it.vintage_from or it.manager or it.fund:
            conds = ["p.vehicle_type = 'fund'"]
        if it.strategy:
            conds.append(f"f.strategy = '{it.strategy}'")
        if it.vintage_from:
            conds.append(f"f.vintage BETWEEN {it.vintage_from} AND {it.vintage_to}")
        if it.manager:
            conds.append(f"m.name ILIKE '{it.manager}%'")
        if it.fund:
            conds.append(f"f.name = '{it.fund}'")
        return " AND ".join(conds)

    def _perf_rows(self, it, ans):
        q = f"""
WITH lr AS (SELECT fund_id, max(as_of) AS q FROM gold.reports WHERE as_of <= $d GROUP BY fund_id),
     cf AS (SELECT position_id,
                   sum(CASE WHEN kind = 'call' THEN amount ELSE 0 END) AS called,
                   sum(CASE WHEN kind = 'dist' THEN amount ELSE 0 END) AS distributed,
                   sum(CASE WHEN kind = 'call' AND value_date > $d - INTERVAL 12 MONTH THEN amount ELSE 0 END) AS called_12m,
                   sum(CASE WHEN kind = 'call' AND value_date BETWEEN $ps AND $pe THEN amount ELSE 0 END) AS called_period,
                   sum(CASE WHEN kind = 'dist' AND value_date BETWEEN $ps AND $pe THEN amount ELSE 0 END) AS dist_period
            FROM gold.cashflows WHERE value_date <= $d GROUP BY position_id)
SELECT f.name AS fund, p.commitment, p.plan_tvpi, coalesce(cf.called, 0) AS called, coalesce(cf.distributed, 0) AS distributed,
       coalesce(cf.called_12m, 0) AS called_12m, coalesce(cf.called_period, 0) AS called_period,
       coalesce(cf.dist_period, 0) AS dist_period, r.lp_nav, r.reported_irr, r.reported_tvpi
FROM gold.positions p JOIN gold.funds f ON f.fund_id = p.vehicle_id
JOIN gold.managers m ON m.manager_id = f.manager_id
LEFT JOIN lr ON lr.fund_id = p.vehicle_id LEFT JOIN gold.reports r ON r.fund_id = lr.fund_id AND r.as_of = lr.q
LEFT JOIN cf ON cf.position_id = p.position_id
WHERE {self._scope_sql(it)} AND p.start_date <= $d ORDER BY p.position_id"""
        ps = it.period_start or dt.date(1900, 1, 1)
        pe = it.period_end or it.as_of
        return self.sql(ans, q, {"d": it.as_of, "ps": ps, "pe": pe})

    def t_perf(self, it):
        ans = Answer(foundation=self.key, question="")
        rows = self._perf_rows(it, ans)
        m = it.metric
        per = {}
        for r in rows:
            nav = r["lp_nav"] or 0.0
            c = r["called"]
            per[r["fund"]] = {
                "net_tvpi": (r["distributed"] + nav) / c if c else None,
                "net_dpi": r["distributed"] / c if c else None,
                "net_irr": r["reported_irr"],
                "unfunded": max(r["commitment"] - c, 0.0),
                "calls_next_12m": r["called_12m"],
                "tvpi_vs_plan": ((r["distributed"] + nav) / c - r["plan_tvpi"]) if c else None,
                "distributions": r["dist_period"] if it.period_start else r["distributed"],
                "calls": r["called_period"] if it.period_start else r["called"],
                "commitment": r["commitment"],
                "adjusted_nav": nav,
            }.get(m)
        if m is None or not rows:
            return refuse(self.key, "I couldn't write a query for this metric from the tables I have.")
        fmt = {"net_irr": pct, "net_tvpi": ratio, "net_dpi": ratio, "tvpi_vs_plan": ratio}.get(m, money)
        if it.group_by == "fund" or (m == "tvpi_vs_plan"):
            ans.table = per
            ans.text = "\n".join(f"- {k}: {fmt(v)}" for k, v in per.items())
            ans.shown = [Shown(label=k, value=v) for k, v in per.items()]
            ans.allowed_numbers = [round(v * 100, 1) for v in per.values() if v is not None]
            return ans
        if m in ("net_tvpi", "net_dpi"):
            c = sum(r["called"] for r in rows)
            num = sum(r["distributed"] + (r["lp_nav"] or 0) if m == "net_tvpi" else r["distributed"] for r in rows)
            val = num / c if c else None
        elif m == "net_irr":
            vals = [v for v in per.values() if v is not None]
            val = sum(vals) / len(vals) if vals else None
            ans.allowed_numbers = [round(val * 100, 1)] if val is not None else []
        else:
            val = sum(v for v in per.values() if v is not None)
        ans.value = val
        ans.shown = [Shown(label=m, value=val)]
        ans.text = f"Query result: {m} = {fmt(val)} over {len(rows)} funds."
        return ans

    def t_behind_plan(self, it):
        ans = Answer(foundation=self.key, question="")
        it2 = it.model_copy(update=dict(metric="tvpi_vs_plan"))
        res = self.t_perf(it2)
        ans = res
        ans.items = sorted(k for k, v in res.table.items() if v is not None and v < 0)
        ans.text = "Behind plan: " + ", ".join(ans.items)
        return ans

    def t_issues(self, it):
        ans = Answer(foundation=self.key, question="")
        kinds = it.issue_kinds or ["extension", "restatement", "team_change", "write_down", "incident", "concern"]
        rows = self.sql(ans, f"""SELECT e.doc_id, e.kind, e.quote, e.learnt FROM gold.events e JOIN gold.managers m USING (manager_id)
            WHERE m.name ILIKE $m AND e.learnt <= $d AND e.kind IN ({', '.join(repr(k) for k in kinds)}) ORDER BY e.learnt""",
                        {"m": (it.manager or "") + "%", "d": it.as_of})
        ans.items = sorted({r["doc_id"] for r in rows})
        ans.text = "\n".join(f"- {r['learnt']}: {r['quote']}" for r in rows)
        from ..answer import numbers_in
        ans.allowed_numbers = [x for r in rows for x in numbers_in(r["quote"])]
        return ans

    def t_coinvests(self, it):
        ans = Answer(foundation=self.key, question="")
        rows = self.sql(ans, """SELECT split_part(p.vehicle_name, ' (', 1) AS name FROM gold.positions p
            JOIN gold.managers m ON m.manager_id = p.manager_id WHERE p.vehicle_type = 'coinvest' AND m.name ILIKE $m""",
                        {"m": (it.manager or "") + "%"})
        ans.items = sorted(re.sub(r" (Pty Ltd|Pte Ltd|Inc\.|Ltd|BV|SA|SL|GmbH|KK)$", "", r["name"]) for r in rows)
        ans.text = "Co-investments: " + ", ".join(ans.items)
        return ans

    def t_fees(self, it):
        ans = Answer(foundation=self.key, question="")
        rows = self.sql(ans, """SELECT split_part(p.vehicle_name, ' (', 1) AS name, f.mgmt_fee_pct, f.carry_pct
            FROM gold.coinvest_fees f JOIN gold.positions p ON p.vehicle_id = f.coinvest_id
            JOIN gold.managers m ON m.manager_id = p.manager_id WHERE m.name ILIKE $m""", {"m": (it.manager or "") + "%"})
        ans.table = {re.sub(r" (Pty Ltd|Pte Ltd|Inc\.|Ltd|BV|SA|SL|GmbH|KK)$", "", r["name"]): r["mgmt_fee_pct"] for r in rows}
        ans.allowed_numbers = [r["carry_pct"] for r in rows]
        ans.text = "\n".join(f"- {r['name']}: {r['mgmt_fee_pct']:.2f}% / {r['carry_pct']:.1f}%" for r in rows)
        return ans

    def t_planned(self, it):
        ans = Answer(foundation=self.key, question="")
        rows = self.sql(ans, "SELECT fund_name, proposed_commitment FROM gold.planned")
        ans.value = rows[0]["proposed_commitment"] if rows else None
        ans.text = f"Planned: {money(ans.value)}"
        ans.shown = [Shown(label="planned", value=ans.value)]
        return ans

    def t_people_where(self, it):
        ans = Answer(foundation=self.key, question="")
        rows = self.sql(ans, """SELECT DISTINCT m2.name FROM gold.people a JOIN gold.managers m1 ON m1.manager_id = a.manager_id
            JOIN gold.people b ON b.person_id = a.person_id AND b.start_date >= a.end_date
            JOIN gold.managers m2 ON m2.manager_id = b.manager_id
            WHERE a.name ILIKE $p AND m1.name ILIKE $m""", {"p": it.person or "", "m": (it.manager or "") + "%"})
        ans.items = sorted(r["name"] for r in rows)
        ans.text = "Joined: " + ", ".join(ans.items)
        return ans

    def t_people_moves(self, it):
        ans = Answer(foundation=self.key, question="")
        rows = self.sql(ans, """SELECT DISTINCT m2.name FROM gold.people a JOIN gold.managers m1 ON m1.manager_id = a.manager_id
            JOIN gold.people b ON b.person_id = a.person_id AND b.start_date >= a.end_date
            JOIN gold.managers m2 ON m2.manager_id = b.manager_id WHERE m1.name ILIKE $m""", {"m": (it.manager or "") + "%"})
        ans.items = sorted(r["name"] for r in rows)
        ans.text = "Managers: " + ", ".join(ans.items)
        return ans

    def t_history(self, it):
        ans = Answer(foundation=self.key, question="")
        rows = self._perf_rows(it.model_copy(update=dict(as_of=it.as_of)), ans)
        iss = self.t_issues(it.model_copy(update=dict(issue_kinds=[])))
        total = sum(r["commitment"] for r in rows)
        ans.composite = dict(commitment=total, funds=[r["fund"] for r in rows], issues=iss.items)
        ans.value = total
        ans.text = f"Committed {money(total)} to " + ", ".join(r["fund"] for r in rows) + ".\n" + iss.text
        ans.shown = [Shown(label="commitment", value=total)]
        ans.allowed_numbers = iss.allowed_numbers + [r["commitment"] for r in rows]
        ans.sql += "\n\n" + iss.sql
        return ans

    def t_advice(self, it):
        return refuse(self.key, "That's a decision, not a query.")
