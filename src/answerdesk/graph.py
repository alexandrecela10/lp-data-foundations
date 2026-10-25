"""The graph: ownership routes and company identity, built from gold for one as-of date.

Nodes: the LP, funds, funds of funds, co-investments, names as reported, companies, managers, people.
Edges: holds (share or value), is (a reported name is a company, with match method), parent of
(holding company to operating company), manages, worked at, alongside.

NetworkX runs it in memory (pure Python, deploys anywhere). The same route question is also
written as SQL/PGQ for DuckPGQ (a DuckDB community extension) and timed in scale.py when the
extension loads; recursive SQL in the semantic layer is the fallback.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

import networkx as nx

from .pipeline import normalise

LP = "LP"


@dataclass
class Hop:
    src: str
    dst: str
    label: str
    factor: float | None


def build(con, d: dt.date) -> nx.DiGraph:
    g = nx.DiGraph()
    g.add_node(LP, kind="lp", label="Aldermoor Pension Plan")
    for fid, name, mid, kind in con.execute("SELECT fund_id, name, manager_id, kind FROM gold.funds").fetchall():
        g.add_node(fid, kind=kind, label=name)
    for mid, name in con.execute("SELECT manager_id, name FROM gold.managers").fetchall():
        g.add_node(mid, kind="manager", label=name)
    for fid, mid in con.execute("SELECT fund_id, manager_id FROM gold.funds").fetchall():
        g.add_edge(mid, fid, rel="manages")
    for cid, name, parent, holdco in con.execute("SELECT company_id, name, parent_id, is_holdco FROM gold.companies").fetchall():
        g.add_node(cid, kind="holdco" if holdco else "company", label=name)
        if parent:
            g.add_edge(parent, cid, rel="parent_of", factor=1.0)
    # LP -> fund / fund of funds, share from the latest report known by d
    for pid, vid, vtype, acq, share, doc in con.execute("""
        SELECT p.position_id, p.vehicle_id, p.vehicle_type, p.acquired, r.lp_share, r.doc_id
        FROM gold.positions p JOIN (SELECT fund_id, max(as_of) q FROM gold.reports WHERE as_of <= $d AND learnt <= $d GROUP BY 1) m
          ON m.fund_id = p.vehicle_id
        JOIN gold.reports r ON r.fund_id = m.fund_id AND r.as_of = m.q
        WHERE p.start_date <= $d""", {"d": d}).fetchall():
        g.add_edge(LP, vid, rel="holds", factor=share, route_kind="fof" if vtype == "fof" else
                   ("secondary" if acq == "secondary" else "fund"), source=doc)
    for fof, fid, share, doc in con.execute("""
        SELECT s.fof_id, s.fund_id, s.share, s.doc_id FROM gold.fof_stakes s
        JOIN (SELECT fof_id, max(as_of) q FROM gold.fof_stakes WHERE as_of <= $d AND learnt <= $d GROUP BY 1) m
          ON m.fof_id = s.fof_id AND m.q = s.as_of""", {"d": d}).fetchall():
        g.add_edge(fof, fid, rel="holds", factor=share, source=doc)
    # fund -> name as reported (value), latest report known by d, own report first
    for fid, nm, val, asof, doc in con.execute("""
        SELECT h.fund_id, h.name_reported, h.value, h.as_of, h.doc_id FROM gold.holdings h
        JOIN (SELECT fund_id, max(as_of) q FROM gold.holdings WHERE as_of <= $d AND learnt <= $d GROUP BY 1) m
          ON m.fund_id = h.fund_id AND m.q = h.as_of
        WHERE h.learnt <= $d
        QUALIFY row_number() OVER (PARTITION BY h.fund_id, h.name_reported ORDER BY CASE h.via WHEN 'own' THEN 0 ELSE 1 END) = 1""",
                                                {"d": d}).fetchall():
        n = f"name:{nm}"
        g.add_node(n, kind="name", label=nm)
        g.add_edge(fid, n, rel="holds_value", value=val, as_of=asof, source=doc)
    # co-investments
    for cid, pid, vname, along in con.execute("""SELECT p.vehicle_id, p.position_id, p.vehicle_name, NULL FROM gold.positions p
        WHERE p.vehicle_type = 'coinvest' AND p.start_date <= $d""", {"d": d}).fetchall():
        g.add_node(cid, kind="coinvest", label="Co-investment " + vname.split(" (")[0])
        g.add_edge(LP, cid, rel="holds", factor=1.0, route_kind="coinvest")
    for cid, nm, val, asof, doc in con.execute("""
        SELECT c.coinvest_id, c.name_reported, c.value, c.as_of, c.doc_id FROM gold.coinvest_values c
        JOIN (SELECT coinvest_id, max(as_of) q FROM gold.coinvest_values WHERE as_of <= $d AND learnt <= $d GROUP BY 1) m
          ON m.coinvest_id = c.coinvest_id AND m.q = c.as_of""", {"d": d}).fetchall():
        n = f"name:{nm}"
        g.add_node(n, kind="name", label=nm)
        g.add_edge(cid, n, rel="holds_value", value=val, as_of=asof, source=doc)
    # identity: a name as reported is a company (exact or holding company name), or links by abbreviation
    for nm, exact, cid, method, conf in con.execute("""SELECT name_reported, company_id_exact, company_id, method, confidence
        FROM gold.identity WHERE status = 'accepted'""").fetchall():
        n = f"name:{nm}"
        if n not in g:
            continue
        if method == "holding company":
            g.add_edge(n, exact, rel="is", method="exact name of the holding company", confidence=conf, factor=1.0)
        else:
            g.add_edge(n, cid, rel="is", method=method, confidence=conf, factor=1.0)
    # people
    for pid, name, mid, start, end, title in con.execute("SELECT * FROM gold.people").fetchall():
        g.add_node(pid, kind="person", label=name)
        g.add_edge(pid, mid, rel="worked_at", start=start, end=end, title=title)
    return g


def event_factors(con, d: dt.date) -> dict:
    """(fund or co-investment id, company id) -> factor from accepted write-downs and exits learnt by d."""
    out = {}
    for kind, factor, fund, co, cid, eff in con.execute("""SELECT kind, factor, event_fund_id, event_coinvest_id, company_id, effective
        FROM gold.events WHERE status = 'accepted' AND kind IN ('write_down', 'exit') AND learnt <= ?""", [d]).fetchall():
        for holder in [x for x in (fund, co) if x]:
            k = (holder, cid if holder == fund else None)
            f = 0.0 if kind == "exit" else factor
            out.setdefault(k, []).append((eff, f))
    return out


def resolve(g: nx.DiGraph, name: str) -> str | None:
    """Company node for a name: a company's legal name, a reported name linked by an identity edge,
    or a holding company with one operating company under it."""
    key = normalise(name)
    for n, a in g.nodes(data=True):
        if a.get("kind") == "company" and normalise(a["label"]) == key:
            return n
    alias = f"name:{name.strip()}"
    cands = [alias] + [n for n, a in g.nodes(data=True) if a.get("kind") == "name" and normalise(a["label"]) == key]
    for c in cands:
        if c in g:
            for _, dst, e in g.out_edges(c, data=True):
                if e.get("rel") == "is":
                    return _down_holdco(g, dst)
    for n, a in g.nodes(data=True):
        if a.get("kind") == "holdco" and normalise(a["label"]) == key:
            return _down_holdco(g, n)
    return None


def _down_holdco(g, n):
    if g.nodes[n].get("kind") == "holdco":
        kids = [d for _, d, e in g.out_edges(n, data=True) if e.get("rel") == "parent_of"]
        if len(kids) == 1:
            return kids[0]
    return n


def routes(g: nx.DiGraph, company: str, d: dt.date, factors: dict | None = None, cutoff: int = 7) -> list[dict]:
    """Every simple path LP -> ... -> company over holds / holds_value / is / parent_of edges.
    Value = product of shares x value on the holds_value edge x event factor. Cycle-free by construction
    (simple paths), depth-limited by cutoff."""
    sub = ownership_view(g)
    out = []
    factors = factors or {}
    for path in nx.all_simple_paths(sub, LP, company, cutoff=cutoff):
        mult, value, asof, srcs, hops = 1.0, None, None, [], []
        holder = None
        for u, v in zip(path, path[1:]):
            e = g.edges[u, v]
            if e["rel"] == "holds":
                mult *= e["factor"]
                hops.append(Hop(u, v, f"holds {e['factor'] * 100:.2f}%", e["factor"]))
            elif e["rel"] == "holds_value":
                value, asof, holder = e["value"], e["as_of"], u
                hops.append(Hop(u, v, f"${e['value']:,.2f}m as of {e['as_of']}", None))
            elif e["rel"] == "is":
                hops.append(Hop(u, v, f"same company ({e['method']})", None))
            else:
                hops.append(Hop(u, v, "only asset of the holding company", None))
            if e.get("source"):
                srcs.append(e["source"])
        if value is None:
            continue
        fac = 1.0
        key_f = (holder, company) if g.nodes[holder].get("kind") != "coinvest" else (holder, None)
        for eff, f in factors.get(key_f, []):
            if eff > asof:
                fac = 0.0 if f == 0.0 else fac * f
        kind = g.edges[LP, path[1]].get("route_kind", "fund")
        out.append(dict(path=path, labels=[g.nodes[n]["label"] for n in path], hops=hops, kind=kind,
                        value=value * mult * fac, before_events=value * mult, factor=fac, as_of=asof, sources=srcs))
    return sorted(out, key=lambda r: -r["value"])


def ownership_view(g: nx.DiGraph) -> nx.DiGraph:
    """A copy with only ownership and identity edges (cached on the graph)."""
    if "_own" not in g.graph:
        keep = {"holds", "holds_value", "is", "parent_of"}
        h = nx.DiGraph()
        h.add_edges_from((u, v) for u, v, e in g.edges(data=True) if e.get("rel") in keep)
        g.graph["_own"] = h
    return g.graph["_own"]


def all_exposures(g: nx.DiGraph, factors: dict | None = None) -> dict:
    """Graph-only sums (optional foundation E): one walk from the LP, carrying our share down each
    route and adding the value at every company reached. No events by as-of date beyond `factors`."""
    factors = factors or {}
    out: dict = {}
    stack = [(LP, 1.0, None, None, (LP,))]
    while stack:
        node, mult, val, holder, path = stack.pop()
        for _, nxt, e in g.out_edges(node, data=True):
            rel = e.get("rel")
            if nxt in path or len(path) > 7 or rel not in ("holds", "holds_value", "is", "parent_of"):
                continue
            if rel == "holds":
                stack.append((nxt, mult * e["factor"], None, None, path + (nxt,)))
            elif rel == "holds_value":
                stack.append((nxt, mult, e["value"], (node, e["as_of"]), path + (nxt,)))
            else:
                stack.append((nxt, mult, val, holder, path + (nxt,)))
                if g.nodes[nxt].get("kind") == "company" and val is not None:
                    fac = 1.0
                    key = (holder[0], nxt) if g.nodes[holder[0]].get("kind") != "coinvest" else (holder[0], None)
                    for eff, f in factors.get(key, []):
                        if eff > holder[1]:
                            fac = 0.0 if f == 0.0 else fac * f
                    out[nxt] = out.get(nxt, 0.0) + val * mult * fac
    return out


def former_partner_moves(g: nx.DiGraph, manager_id: str) -> list[dict]:
    out = []
    for p, a in g.nodes(data=True):
        if a.get("kind") != "person":
            continue
        jobs = [(dst, e) for _, dst, e in g.out_edges(p, data=True) if e.get("rel") == "worked_at"]
        left = [e for dst, e in jobs if dst == manager_id and e.get("end") is not None]
        for e0 in left:
            for dst, e in jobs:
                if dst != manager_id and e["start"] >= e0["end"]:
                    out.append(dict(person=a["label"], left=e0["end"], joined=g.nodes[dst]["label"],
                                    joined_id=dst, start=e["start"]))
    return out


def coinvests_alongside(con, manager_id: str) -> list[str]:
    return [r[0] for r in con.execute("""SELECT split_part(vehicle_name, ' (', 1) FROM gold.positions
        WHERE vehicle_type = 'coinvest' AND manager_id = ?""", [manager_id]).fetchall()]


# ------------------------------------------------------------------ the same question three ways (for teaching)

SQL_JOINS = """-- Plain SQL with joins: one SELECT per route shape, glued with UNION ALL.
-- Every new shape (a fund of funds inside a fund of funds) needs another block.
SELECT 'direct fund' AS route, p.vehicle_id, r.lp_share * h.value AS value
FROM positions p JOIN reports r ON r.fund_id = p.vehicle_id
JOIN holdings h ON h.fund_id = p.vehicle_id
WHERE h.company_id = 'C0001'
UNION ALL
SELECT 'fund of funds', s.fund_id, r.lp_share * s.share * h.value
FROM positions p JOIN reports r ON r.fund_id = p.vehicle_id
JOIN fof_stakes s ON s.fof_id = p.vehicle_id
JOIN holdings h ON h.fund_id = s.fund_id
WHERE h.company_id = 'C0001'
UNION ALL
SELECT 'co-investment', c.coinvest_id, c.value
FROM coinvest_values c WHERE c.company_id = 'C0001';
-- (plus: latest report per fund, events after the report, own report over a copy)"""

PGQ = """-- SQL/PGQ (ISO SQL:2023) on DuckDB with the DuckPGQ extension.
CREATE PROPERTY GRAPH holdings_graph
  VERTEX TABLES (nodes)
  EDGE TABLES (edges SOURCE KEY (src) REFERENCES nodes (id)
                     DESTINATION KEY (dst) REFERENCES nodes (id));
-- every route of 2 to 5 hops from the LP to Calder Packaging
FROM GRAPH_TABLE (holdings_graph
  MATCH p = (lp:nodes WHERE lp.id = 'LP')-[e:edges]->{2,5}(c:nodes WHERE c.id = 'C0001')
  COLUMNS (vertices(p) AS route));
-- DuckPGQ returns one path per pair for variable-length patterns (ANY SHORTEST),
-- so listing every route takes one fixed-length MATCH per length, joined with UNION ALL."""

CYPHER = """// The same question in Cypher (property-graph query language)
MATCH p = (lp:LP)-[:HOLDS|HOLDS_VALUE|IS|PARENT_OF*1..7]->(c:Company {name: 'Calder Packaging Ltd'})
RETURN [n IN nodes(p) | n.label] AS route,
       reduce(v = 1.0, r IN relationships(p) | v * coalesce(r.share, r.value, 1.0)) AS value"""

SEMANTIC = """# Semantic layer request: pick a governed metric, filters and a date. No SQL, no joins.
metric: lookthrough_exposure      # v2, owner Risk team
company: Calder Packaging
as_of: 2026-10-26
group_by: route"""
