"""Bronze, silver, gold in DuckDB.

bronze: every document as received (text or row), with learnt_at and as_of.
silver: documents read into fixed fields, each row checked by its contract (contracts.py);
        failures go to silver.rejects with the reason. Company identity matching lives here.
gold:   deduplicated, typed tables that the semantic layer, the SQL writer and the graph read.
        Every gold row keeps the doc_id it came from (lineage).
"""
from __future__ import annotations

import datetime as dt
import json
import re
import time
from dataclasses import dataclass, field

import duckdb
from pydantic import ValidationError

from .contracts import CashFlowRow, EventRow, HoldingRow, ReportRow
from .sources import Doc, render
from .world import World, generate

LEGAL_FORMS = ["pte ltd", "pty ltd", "limited", "ltd", "gmbh", "inc", "sa", "sl", "bv", "kk"]
MONTHS = {m: i + 1 for i, m in enumerate(["January", "February", "March", "April", "May", "June", "July",
                                         "August", "September", "October", "November", "December"])}


def normalise(name: str) -> str:
    s = re.sub(r"[^a-z0-9 ]", " ", name.lower())
    s = re.sub(r"\s+", " ", s).strip()
    for lf in LEGAL_FORMS:
        if s.endswith(" " + lf):
            s = s[: -len(lf) - 1]
            break
    return s.strip()


def _date(s: str) -> dt.date:
    s = s.strip()
    if re.match(r"\d{4}-\d{2}-\d{2}$", s):
        return dt.date.fromisoformat(s)
    d, m, y = s.split()
    return dt.date(int(y), MONTHS[m], int(d))


def _amount_usd(s: str) -> float:
    if not re.fullmatch(r"USD \d{1,3}(,\d{3})*\.\d{2}", s.strip()):
        raise ValueError(f"amount format not recognised: {s.strip()!r}")
    return float(s.strip()[4:].replace(",", "")) / 1e6


@dataclass
class Store:
    con: duckdb.DuckDBPyConnection
    world: World
    docs: list
    timings: dict = field(default_factory=dict)
    counts: dict = field(default_factory=dict)

    def q(self, sql: str, params=None):
        return self.con.execute(sql, params or []).fetchall()

    def df(self, sql: str, params=None):
        return self.con.execute(sql, params or []).df()


def _insert(con, table: str, rows: list) -> None:
    """Bulk insert through a DataFrame (executemany is slow in DuckDB)."""
    if not rows:
        return
    import pandas as pd
    cols = [r[0] for r in con.execute(f"DESCRIBE {table}").fetchall()]
    df = pd.DataFrame([list(r) for r in rows], columns=cols)
    con.register("_tmp_rows", df)
    con.execute(f"INSERT INTO {table} SELECT * FROM _tmp_rows")
    con.unregister("_tmp_rows")


# ------------------------------------------------------------------ bronze

def load_bronze(con, docs: list[Doc]) -> None:
    con.execute("CREATE SCHEMA IF NOT EXISTS bronze")
    con.execute("""CREATE OR REPLACE TABLE bronze.documents (doc_id VARCHAR PRIMARY KEY, source VARCHAR, kind VARCHAR,
                   learnt_at DATE, as_of DATE, text VARCHAR, row_json VARCHAR, restricted_to VARCHAR)""")
    _insert(con, "bronze.documents", [
        (d.doc_id, d.source, d.kind, d.learnt_at, d.as_of, d.text, json.dumps(d.row, default=str),
         ",".join(d.restricted_to)) for d in docs])


# ------------------------------------------------------------------ silver

def _reject(rej, d, reason):
    rej.append((d.doc_id, d.source, str(reason)[:300]))


def build_silver(con, docs: list[Doc]) -> dict:
    con.execute("CREATE SCHEMA IF NOT EXISTS silver")
    rej: list = []
    by_kind: dict[str, list[Doc]] = {}
    for d in docs:
        by_kind.setdefault(d.kind, []).append(d)

    # reference
    comp = [d.row for d in by_kind.get("company", [])]
    mgr = [d.row for d in by_kind.get("manager", [])]
    fnd = [d.row for d in by_kind.get("fund", [])]
    ppl = [d.row for d in by_kind.get("person", [])]
    con.execute("CREATE OR REPLACE TABLE silver.companies (company_id VARCHAR, name VARCHAR, name_key VARCHAR, sector VARCHAR, country VARCHAR, region VARCHAR, parent_id VARCHAR, is_holdco BOOLEAN)")
    _insert(con, "silver.companies", [(r["company_id"], r["name"], normalise(r["name"]), r["sector"], r["country"], r["region"],
                      r["parent_id"] or None, r["is_holdco"]) for r in comp])
    con.execute("CREATE OR REPLACE TABLE silver.managers (manager_id VARCHAR, name VARCHAR, strategy VARCHAR, region VARCHAR, kind VARCHAR)")
    _insert(con, "silver.managers", [tuple(r.values()) for r in mgr])
    con.execute("CREATE OR REPLACE TABLE silver.funds (fund_id VARCHAR, manager_id VARCHAR, name VARCHAR, vintage INT, strategy VARCHAR, region VARCHAR, size DOUBLE, kind VARCHAR)")
    _insert(con, "silver.funds", [tuple(r.values()) for r in fnd])
    con.execute("CREATE OR REPLACE TABLE silver.people (person_id VARCHAR, name VARCHAR, manager_id VARCHAR, start_date DATE, end_date DATE, title VARCHAR)")
    _insert(con, "silver.people", [(r["person_id"], r["name"], r["manager_id"], r["start"], r["end"], r["title"]) for r in ppl])
    fund_by_name = {r["name"].lower(): r["fund_id"] for r in fnd}

    # holdings snapshot
    pos = [d.row for d in by_kind.get("position", [])]
    con.execute("""CREATE OR REPLACE TABLE silver.positions (position_id VARCHAR, vehicle_id VARCHAR, vehicle_name VARCHAR,
        vehicle_type VARCHAR, manager_id VARCHAR, acquired VARCHAR, commitment DOUBLE, start_date DATE, purchase_price DOUBLE,
        unfunded_at_purchase DOUBLE, plan_tvpi DOUBLE, plan_irr DOUBLE, mgmt_fee_pct DOUBLE, carry_pct DOUBLE, doc_id VARCHAR)""")
    _insert(con, "silver.positions", [
        (r["position_id"], r["vehicle_id"], r["vehicle_name"], r["vehicle_type"], r["manager_id"], r["acquired"],
         r["commitment"], r["start_date"], r["purchase_price"], r["unfunded_at_purchase"], r["plan_tvpi"],
         r["plan_irr"], r.get("mgmt_fee_pct"), r.get("carry_pct"), d.doc_id)
        for d, r in ((d, d.row) for d in by_kind.get("position", []))])
    con.execute("CREATE OR REPLACE TABLE silver.planned (manager_id VARCHAR, fund_name VARCHAR, proposed_commitment DOUBLE, status VARCHAR, doc_id VARCHAR)")
    _insert(con, "silver.planned", [(d.row["manager_id"], d.row["fund_name"], d.row["proposed_commitment"], d.row["status"], d.doc_id)
                     for d in by_kind.get("planned", [])])
    pos_by_name = {r["vehicle_name"].lower(): r["position_id"] for r in pos}

    # notices -> cash flows
    flows: dict[str, tuple] = {}
    for kind in ("call", "dist", "purchase"):
        for d in by_kind.get(kind, []):
            t = d.text
            try:
                subj = re.search(r"Subject: (?:CORRECTED )?(?:Capital call notice, |Distribution notice, |Completion statement, purchase of an interest in )(.+)", t).group(1).strip()
                ref = re.search(r"Reference: (\S+)", t).group(1)
                pid = pos_by_name[subj.lower()]
                if kind == "call":
                    amt = _amount_usd(re.search(r"Amount due: (.+)", t).group(1))
                    nd, vd, rec = _date(re.search(r"Notice date: (\S+)", t).group(1)), _date(re.search(r"Due date: (\S+)", t).group(1)), 0.0
                elif kind == "dist":
                    amt = _amount_usd(re.search(r"Amount: (.+)", t).group(1))
                    rec = _amount_usd(re.search(r"Of which recallable: (.+)", t).group(1))
                    nd, vd = _date(re.search(r"Notice date: (\S+)", t).group(1)), _date(re.search(r"Distribution date: (\S+)", t).group(1))
                else:
                    amt = _amount_usd(re.search(r"Purchase price paid: (.+)", t).group(1))
                    nd = vd = _date(re.search(r"Completion date: (\S+)", t).group(1))
                row = CashFlowRow(ref=ref, position_id=pid, kind=kind, amount=amt, recallable=rec, notice_date=nd,
                                  value_date=vd, doc_id=d.doc_id)
                flows[ref] = (row.ref, row.position_id, row.kind, row.amount, row.recallable, row.notice_date,
                              row.value_date, row.doc_id)
            except (ValueError, ValidationError, AttributeError, KeyError) as e:
                _reject(rej, d, e)
    con.execute("CREATE OR REPLACE TABLE silver.cashflows (ref VARCHAR, position_id VARCHAR, kind VARCHAR, amount DOUBLE, recallable DOUBLE, notice_date DATE, value_date DATE, doc_id VARCHAR)")
    _insert(con, "silver.cashflows", list(flows.values()))

    # reports -> report rows, holding rows, fof stakes
    reps, hold, stakes, cos = [], [], [], []
    for d in by_kind.get("fund_report", []):
        try:
            r, h, s = _parse_report(d, fund_by_name)
            reps.append(r)
            hold += h
            stakes += s
        except (ValueError, ValidationError, AttributeError, KeyError) as e:
            _reject(rej, d, e)
    for d in by_kind.get("coinvest_statement", []):
        t = d.text
        cid = re.search(r"Reference: (\S+)", t).group(1)
        name = re.search(r"Co-investment statement: (.+)", t).group(1).split(" (")[0].strip()
        val = float(re.search(r"Your value: \$([\d,.]+)m", t).group(1).replace(",", ""))
        cos.append((cid, name, d.as_of, d.learnt_at, val, d.doc_id))
    fees = []
    for d in by_kind.get("coinvest_fees", []):
        t = d.text
        fees.append((re.search(r"Reference: (\S+)", t).group(1), float(re.search(r"Management fee: ([\d.]+)%", t).group(1)),
                     float(re.search(r"Carried interest: ([\d.]+)%", t).group(1)), d.doc_id))
    con.execute("CREATE OR REPLACE TABLE silver.reports (fund_id VARCHAR, as_of DATE, learnt DATE, fund_nav DOUBLE, lp_share DOUBLE, lp_nav DOUBLE, reported_irr DOUBLE, reported_tvpi DOUBLE, doc_id VARCHAR)")
    _insert(con, "silver.reports", reps)
    con.execute("CREATE OR REPLACE TABLE silver.report_holdings (fund_id VARCHAR, manager_id VARCHAR, as_of DATE, learnt DATE, name_reported VARCHAR, value DOUBLE, doc_id VARCHAR, via VARCHAR)")
    _insert(con, "silver.report_holdings", hold)
    con.execute("CREATE OR REPLACE TABLE silver.fof_stakes (fof_id VARCHAR, fund_id VARCHAR, share DOUBLE, as_of DATE, learnt DATE, doc_id VARCHAR)")
    _insert(con, "silver.fof_stakes", stakes)
    con.execute("CREATE OR REPLACE TABLE silver.coinvest_statements (coinvest_id VARCHAR, name_reported VARCHAR, as_of DATE, learnt DATE, value DOUBLE, doc_id VARCHAR)")
    _insert(con, "silver.coinvest_statements", cos)
    con.execute("CREATE OR REPLACE TABLE silver.coinvest_fees (coinvest_id VARCHAR, mgmt_fee_pct DOUBLE, carry_pct DOUBLE, doc_id VARCHAR)")
    _insert(con, "silver.coinvest_fees", fees)

    # letters -> events
    letters = by_kind.get("letter", [])
    con.execute("CREATE OR REPLACE TABLE silver.letters (doc_id VARCHAR, manager_name VARCHAR, learnt DATE, text VARCHAR)")
    _insert(con, "silver.letters", [
        (d.doc_id, re.search(r"From: (.+)", d.text).group(1).strip(), d.learnt_at, d.text) for d in letters])
    mgr_by_name = {r["name"]: r["manager_id"] for r in mgr}
    evs = []
    for d in letters:
        for e in read_events(d, mgr_by_name):
            evs.append(e)
    con.execute("""CREATE OR REPLACE TABLE silver.events (event_id VARCHAR, doc_id VARCHAR, manager_id VARCHAR, kind VARCHAR,
        company_name VARCHAR, person_name VARCHAR, fund_id VARCHAR, coinvest_id VARCHAR, factor DOUBLE, effective DATE,
        learnt DATE, confidence DOUBLE, status VARCHAR, quote VARCHAR)""")
    _insert(con, "silver.events", [tuple(e.model_dump().values()) for e in evs])

    # news (kept for search and triggers only)
    con.execute("CREATE OR REPLACE TABLE silver.news (doc_id VARCHAR, ts TIMESTAMP, text VARCHAR)")
    _insert(con, "silver.news", [(d.doc_id, d.row["ts"], d.text) for d in by_kind.get("news", [])])

    con.execute("CREATE OR REPLACE TABLE silver.rejects (doc_id VARCHAR, source VARCHAR, reason VARCHAR)")
    if rej:
        _insert(con, "silver.rejects", rej)
    build_identity(con)
    return {"rejects": len(rej)}


def _pct(s: str) -> float | None:
    s = s.strip()
    return None if s in ("n/m", "") else float(s.rstrip("%")) / 100


def _parse_report(d: Doc, fund_by_name: dict):
    t = d.text
    lines = t.splitlines()
    hold, stakes = [], []
    if ", quarterly statement, as of" in lines[0]:                      # fund of funds layout
        fname = lines[0].split(", quarterly statement")[0]
        fid = fund_by_name[fname.lower()]
        nav = float(re.search(r"Fund of funds net asset value: \$([\d,.]+)m", t).group(1).replace(",", ""))
        share = float(re.search(r"Your share of the fund of funds: ([\d.]+)%", t).group(1)) / 100
        lpnav = float(re.search(r"Your net asset value: \$([\d,.]+)m", t).group(1).replace(",", ""))
        for m in re.finditer(r"\* (.+?): Selbrook share ([\d.]+)%", t):
            stakes.append((fid, fund_by_name[m.group(1).lower()], float(m.group(2)) / 100, d.as_of, d.learnt_at, d.doc_id))
        for m in re.finditer(r"\* (.+?) \| (.+?) \| ([\d.]+)$", t, re.M):
            hold.append(HoldingRow(fund_id=fund_by_name[m.group(1).lower()], as_of=d.as_of, learnt=d.learnt_at,
                                   name_reported=m.group(2).strip(), value=float(m.group(3)), doc_id=d.doc_id, via="fof_copy"))
        irr = tv = None
    elif "Quarterly report to investors" in t:                          # layout 0
        fid = fund_by_name[lines[0].strip().lower()]
        nav = float(re.search(r"Fund net asset value: \$([\d,.]+)m", t).group(1).replace(",", ""))
        irr = _pct(re.search(r"Net IRR since inception \(fund level, incl\. credit facility\): (\S+)", t).group(1))
        tv = float(re.search(r"Net TVPI \(fund level\): ([\d.]+)x", t).group(1))
        share = float(re.search(r"Your share of the fund: ([\d.]+)%", t).group(1)) / 100
        lpnav = float(re.search(r"Your net asset value: \$([\d,.]+)m", t).group(1).replace(",", ""))
        for m in re.finditer(r"^\| (.+?) \| (.+?) \| (.+?) \| ([\d,.]+) \|$", t, re.M):
            if m.group(1) == "Company":
                continue
            hold.append(HoldingRow(fund_id=fid, as_of=d.as_of, learnt=d.learnt_at, name_reported=m.group(1).strip(),
                                   value=float(m.group(4).replace(",", "")), doc_id=d.doc_id, via="own"))
    elif " - Investor Report" in lines[0]:                              # layout 1
        fid = fund_by_name[lines[0].split(" - Investor Report")[0].lower()]
        nav = float(re.search(r"NAV \(USD m\): ([\d.]+)", t).group(1))
        irr = _pct(re.search(r"Reported net IRR: (\S+)", t).group(1))
        tv = float(re.search(r"Reported net TVPI: ([\d.]+)x", t).group(1))
        share = float(re.search(r"ownership ([\d.]+)%", t).group(1)) / 100
        lpnav = float(re.search(r"; NAV USD ([\d.]+)m", t).group(1))
        for m in re.finditer(r"^- (.+) - USD ([\d.]+)m$", t, re.M):
            hold.append(HoldingRow(fund_id=fid, as_of=d.as_of, learnt=d.learnt_at, name_reported=m.group(1).strip(),
                                   value=float(m.group(2)), doc_id=d.doc_id, via="own"))
    elif ";REPORT;" in lines[0]:                                        # layout 2
        fid = fund_by_name[lines[0].split(";")[0].lower()]
        kv = {}
        for ln in lines[1:]:
            parts = ln.split(";")
            if parts[0] == "holding":
                hold.append(HoldingRow(fund_id=fid, as_of=d.as_of, learnt=d.learnt_at, name_reported=parts[1].strip(),
                                       value=float(parts[2]), doc_id=d.doc_id, via="own"))
            else:
                kv[parts[0]] = parts[1]
        nav, share, lpnav = float(kv["fund_nav_usd_m"]), float(kv["lp_ownership_pct"]) / 100, float(kv["lp_nav_usd_m"])
        irr, tv = _pct(kv["reported_net_irr"]), float(kv["reported_net_tvpi"])
    else:
        raise ValueError("unknown report layout")
    r = ReportRow(fund_id=fid, as_of=d.as_of, learnt=d.learnt_at, fund_nav=nav, lp_share=share, lp_nav=lpnav,
                  reported_irr=irr, reported_tvpi=tv, doc_id=d.doc_id)
    mid = None
    hrows = [(h.fund_id, mid, h.as_of, h.learnt, h.name_reported, h.value, h.doc_id, h.via) for h in hold]
    return tuple(r.model_dump().values()), hrows, stakes


# Patterns the fixed-field letter reader recognises. Anything else is left to search.
PATTERNS = [
    ("write_down", re.compile(r"(?:(?<=\. )|(?<=\n)|^)(?P<company>[A-Z][\w&.\- ]+?) was written down on (?P<date>\d{1,2} \w+ \d{4}) to (?P<factor>[\d.]+) times"), 0.95),
    ("exit", re.compile(r"The sale of (?P<company>[A-Z][\w&.\- ]+?) was agreed on (?P<date>\d{1,2} \w+ \d{4}), at (?P<factor>[\d.]+) times"), 0.95),
    ("team_change", re.compile(r"(?P<person>[A-Z][a-z]+ [A-Z][\w\-]+), a (?:founding )?partner, has left the firm"), 0.9),
    ("restatement", re.compile(r"The valuation of (?P<fund>.+?) as of (?P<date>\d{1,2} \w+ \d{4}) has been restated"), 0.9),
    ("extension", re.compile(r"We extended the investment period of (?P<fund>.+?) by"), 0.9),
    ("concern", re.compile(r"Trading at (?P<company>[A-Z][\w&.\- ]+?) softened"), 0.55),
    ("incident", re.compile(r"We are reviewing a reported (?P<what>[\w ]+?) at a portfolio company"), 0.6),
]


def read_events(d: Doc, mgr_by_name: dict) -> list[EventRow]:
    t = d.text
    mname = re.search(r"From: (.+)", t).group(1).strip()
    mid = mgr_by_name.get(mname, "")
    out = []
    for i, (kind, pat, conf) in enumerate(PATTERNS):
        for m in pat.finditer(t):
            g = m.groupdict()
            eff = _date(g["date"]) if g.get("date") else d.learnt_at
            co_id = None
            if kind == "write_down" and re.search(r"The co-investment in (.+?) is marked at the same multiple", t):
                co_id = re.search(r"The co-investment in (.+?) is marked", t).group(1).strip()
            sent = t[max(0, t.rfind(".", 0, m.start()) + 1): t.find(".", m.end()) + 1].strip()
            out.append(EventRow(event_id=f"{d.doc_id}:{i}:{m.start()}", doc_id=d.doc_id, manager_id=mid, kind=kind,
                                company_name=g.get("company"), person_name=g.get("person"), fund_id=None,
                                coinvest_id=co_id, factor=float(g["factor"]) if g.get("factor") else None,
                                effective=eff, learnt=d.learnt_at, confidence=conf,
                                status="accepted" if conf >= 0.8 else "waiting_for_review", quote=sent))
    return out


def build_identity(con) -> None:
    """Match every reported company name to the reference list: exact (after normalising),
    holding company, or abbreviation. Ambiguous or unknown names wait for a person."""
    comps = con.execute("SELECT company_id, name, name_key, parent_id, is_holdco FROM silver.companies").fetchall()
    by_key = {}
    for cid, name, key, parent, holdco in comps:
        by_key.setdefault(key, []).append(cid)
    kids: dict = {}
    for cid, name, key, parent, holdco in comps:
        if parent:
            kids.setdefault(parent, []).append(cid)
    holdco_ids = {cid for cid, *_r, h in comps if h}
    names = [r[0] for r in con.execute("""SELECT DISTINCT name_reported FROM silver.report_holdings
        UNION SELECT DISTINCT name_reported FROM silver.coinvest_statements
        UNION SELECT DISTINCT company_name FROM silver.events WHERE company_name IS NOT NULL""").fetchall()]
    keys = {k: v for k, v in by_key.items()}
    rows = []
    for n in sorted(names):
        k = normalise(n)
        cand = keys.get(k, [])
        if len(cand) == 1 and cand[0] not in holdco_ids:
            rows.append((n, k, cand[0], cand[0], "exact", 1.0, "accepted"))
            continue
        if len(cand) == 1 and cand[0] in holdco_ids:
            ch = kids.get(cand[0], [])
            if len(ch) == 1:
                rows.append((n, k, cand[0], ch[0], "holding company", 0.95, "accepted"))
            else:
                rows.append((n, k, cand[0], None, "holding company, several assets", 0.5, "waiting_for_review"))
            continue
        toks = k.split()
        hits = []
        if n.strip().endswith(".") and len(toks) >= 2:
            for key, ids in keys.items():
                kt = key.split()
                if len(kt) == len(toks) and kt[:-1] == toks[:-1] and kt[-1].startswith(toks[-1]):
                    hits += ids
        if len(hits) == 1:
            rows.append((n, k, None, hits[0], "abbreviation", 0.9, "accepted"))
        else:
            rows.append((n, k, None, None, "no match" if not hits else "ambiguous abbreviation", 0.0, "waiting_for_review"))
    con.execute("""CREATE OR REPLACE TABLE silver.identity (name_reported VARCHAR, name_key VARCHAR, company_id_exact VARCHAR,
        company_id VARCHAR, method VARCHAR, confidence DOUBLE, status VARCHAR)""")
    _insert(con, "silver.identity", rows)


# ------------------------------------------------------------------ gold

GOLD_SQL = """
CREATE SCHEMA IF NOT EXISTS gold;
CREATE OR REPLACE TABLE gold.companies AS SELECT * FROM silver.companies;
CREATE OR REPLACE TABLE gold.managers AS SELECT * FROM silver.managers;
CREATE OR REPLACE TABLE gold.funds AS SELECT * FROM silver.funds;
CREATE OR REPLACE TABLE gold.people AS SELECT * FROM silver.people;
CREATE OR REPLACE TABLE gold.positions AS SELECT * FROM silver.positions;
CREATE OR REPLACE TABLE gold.planned AS SELECT * FROM silver.planned;
CREATE OR REPLACE TABLE gold.coinvest_fees AS SELECT * FROM silver.coinvest_fees;
CREATE OR REPLACE TABLE gold.cashflows AS SELECT * FROM silver.cashflows;
CREATE OR REPLACE TABLE gold.reports AS SELECT * FROM silver.reports;
CREATE OR REPLACE TABLE gold.fof_stakes AS SELECT * FROM silver.fof_stakes;
CREATE OR REPLACE TABLE gold.letters AS SELECT * FROM silver.letters;
CREATE OR REPLACE TABLE gold.news AS SELECT * FROM silver.news;
CREATE OR REPLACE TABLE gold.identity AS SELECT * FROM silver.identity;
-- every holding row with its identity; queries pick the latest report known by the as-of date, own report first
CREATE OR REPLACE TABLE gold.holdings AS
SELECT h.fund_id, h.as_of, h.learnt, h.name_reported, i.name_key AS company_key,
       c.company_id AS company_id_exact, CASE WHEN i.status = 'accepted' THEN i.company_id END AS company_id,
       i.method AS match_method, h.value, h.doc_id, h.via
FROM silver.report_holdings h
LEFT JOIN silver.identity i ON i.name_reported = h.name_reported
LEFT JOIN silver.companies c ON c.name_key = i.name_key AND NOT c.is_holdco;
CREATE OR REPLACE TABLE gold.coinvest_values AS
SELECT s.coinvest_id, s.name_reported, i.name_key AS company_key, c.company_id AS company_id_exact,
       CASE WHEN i.status = 'accepted' THEN i.company_id END AS company_id, s.as_of, s.learnt, s.value, s.doc_id
FROM silver.coinvest_statements s
LEFT JOIN silver.identity i ON i.name_reported = s.name_reported
LEFT JOIN silver.companies c ON c.name_key = i.name_key AND NOT c.is_holdco;
-- events: link to the fund of the writing manager that holds the company, and to a named co-investment
CREATE OR REPLACE TABLE gold.events AS
SELECT e.*, i.name_key AS company_key, CASE WHEN i.status = 'accepted' THEN i.company_id END AS company_id,
       (SELECT min(h.fund_id) FROM silver.report_holdings h JOIN silver.funds f ON f.fund_id = h.fund_id
         JOIN silver.identity ih ON ih.name_reported = h.name_reported
         WHERE f.manager_id = e.manager_id AND h.via = 'own'
           AND (h.name_reported = e.company_name OR (ih.company_id IS NOT NULL AND ih.company_id = i.company_id))) AS event_fund_id,
       (SELECT min(s.coinvest_id) FROM silver.coinvest_statements s WHERE s.name_reported = e.coinvest_id) AS event_coinvest_id
FROM silver.events e LEFT JOIN silver.identity i ON i.name_reported = e.company_name;
"""


def build(seed: int = 42, scale: int = 1, noisy: bool = False, world: World | None = None) -> Store:
    t0 = time.perf_counter()
    w = world or generate(seed, scale, noisy)
    t1 = time.perf_counter()
    docs = render(w)
    t2 = time.perf_counter()
    con = duckdb.connect()
    load_bronze(con, docs)
    t3 = time.perf_counter()
    info = build_silver(con, docs)
    t4 = time.perf_counter()
    con.execute(GOLD_SQL)
    t5 = time.perf_counter()
    st = Store(con, w, docs)
    st.timings = dict(generate=t1 - t0, render=t2 - t1, bronze=t3 - t2, silver=t4 - t3, gold=t5 - t4)
    st.counts = dict(documents=len(docs), rejects=info["rejects"],
                     **{s: n for s, n in con.execute("SELECT source, count(*) FROM bronze.documents GROUP BY 1").fetchall()})
    return st
