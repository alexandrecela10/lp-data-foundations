"""What changes at 10x and 100x the data. Runs locally; results are committed and the demo reads them.

For each size: build the whole pipeline (documents to gold), then time the same route question
three ways (recursive SQL in the semantic layer, NetworkX graph walk, DuckPGQ when it loads),
a portfolio-wide sum (semantic layer SQL against a graph-only sum, the optional E), and one
governed performance metric. Times are the median of repeated runs, in milliseconds.
"""
from __future__ import annotations

import datetime as dt
import json
import resource
import statistics
import time

from . import access, graph, pipeline
from .semantic.layer import MetricRequest, SemanticLayer
from .world import TODAY


def _t(fn, n=5):
    ts = []
    out = None
    for _ in range(n):
        t0 = time.perf_counter()
        out = fn()
        ts.append((time.perf_counter() - t0) * 1000)
    return statistics.median(ts), out


def pgq_routes(con, company_id: str, d: dt.date) -> tuple[float | None, int | None, str]:
    """Routes to a company with DuckPGQ: one fixed-length MATCH per path length (2 to 5 hops)."""
    try:
        con.execute("LOAD duckpgq")
    except Exception as e:  # extension unavailable on this platform or version
        return None, None, f"DuckPGQ not loaded: {type(e).__name__}"
    g = graph.build(con, d)
    import pandas as pd
    nodes = pd.DataFrame({"id": list(g.nodes)})
    edges = pd.DataFrame([dict(src=u, dst=v) for u, v, e in g.edges(data=True)
                          if e.get("rel") in ("holds", "holds_value", "is", "parent_of")])
    con.register("n_df", nodes)
    con.register("e_df", edges)
    con.execute("CREATE OR REPLACE TABLE pg_nodes AS SELECT * FROM n_df")
    con.execute("CREATE OR REPLACE TABLE pg_edges AS SELECT * FROM e_df")
    try:
        con.execute("DROP PROPERTY GRAPH IF EXISTS hg")
    except Exception:
        pass
    con.execute("""CREATE PROPERTY GRAPH hg VERTEX TABLES (pg_nodes)
        EDGE TABLES (pg_edges SOURCE KEY (src) REFERENCES pg_nodes (id) DESTINATION KEY (dst) REFERENCES pg_nodes (id))""")

    def q():
        total = 0
        for k in range(2, 6):
            hops = "-[e:pg_edges]->(x:pg_nodes)" * (k - 1)
            sql = (f"FROM GRAPH_TABLE (hg MATCH (a:pg_nodes WHERE a.id = 'LP'){hops}-[f:pg_edges]->"
                   f"(c:pg_nodes WHERE c.id = '{company_id}') COLUMNS (a.id AS a))")
            sql = sql.replace("(x:pg_nodes)", "(x{i}:pg_nodes)")
            parts = sql.split("(x{i}:pg_nodes)")
            sql = "".join(p + (f"(x{i}:pg_nodes)" if i < len(parts) - 1 else "") for i, p in enumerate(parts))
            parts = sql.split("-[e:pg_edges]->")
            sql = "".join(p + (f"-[e{i}:pg_edges]->" if i < len(parts) - 1 else "") for i, p in enumerate(parts))
            total += len(con.execute(sql).fetchall())
        return total
    try:
        ms, n = _t(q, 3)
        return ms, n, "ok"
    except Exception as e:
        return None, None, f"DuckPGQ query failed: {str(e)[:120]}"


def run_size(k: int) -> dict:
    t0 = time.perf_counter()
    st = pipeline.build(scale=k)
    build_s = time.perf_counter() - t0
    con = access.role_db(st, "head_of_pe")
    sl = SemanticLayer(st, "head_of_pe", "resolved")
    d = TODAY
    sql_ms, res = _t(lambda: sl.run(MetricRequest(metric="lookthrough_exposure", as_of=d, company="Calder Packaging")))
    gb_ms, g = _t(lambda: graph.build(con, d), 3)
    f = graph.event_factors(con, d)
    walk_ms, rs = _t(lambda: graph.routes(g, "C0001", d, f))
    sum_sql_ms, sres = _t(lambda: sl.run(MetricRequest(metric="lookthrough_exposure", as_of=d, sector="Packaging")), 3)

    def graph_sum():
        ex = graph.all_exposures(g, f)
        return sum(v for c, v in ex.items() if g.nodes[c].get("label", "").find("Packaging") >= 0)
    gsum_ms, gsum = _t(graph_sum, 3)
    perf_ms, _ = _t(lambda: sl.run(MetricRequest(metric="net_tvpi", as_of=dt.date(2026, 9, 30), strategy="buyout")), 3)
    pgq_ms, pgq_n, pgq_status = pgq_routes(con, "C0001", d)
    return dict(scale=k, funds=len(st.world.funds), companies=len(st.world.companies), positions=len(st.world.positions),
                documents=st.counts["documents"], graph_nodes=g.number_of_nodes(), graph_edges=g.number_of_edges(),
                build_s=build_s, pipeline_s=st.timings,
                calder_value_sql=res.numbers[0].value, calder_value_graph=sum(r["value"] for r in rs),
                route_sql_ms=sql_ms, graph_build_ms=gb_ms, route_graph_walk_ms=walk_ms,
                route_graph_total_ms=gb_ms + walk_ms, route_pgq_ms=pgq_ms, route_pgq_paths=pgq_n, pgq_status=pgq_status,
                portfolio_sum_sql_ms=sum_sql_ms, packaging_sum_sql=sres.numbers[0].value, portfolio_sum_graph_only_ms=gsum_ms, packaging_sum_graph_only=gsum, perf_metric_ms=perf_ms,
                max_rss_mb=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024 * 1024 if __import__("sys").platform == "darwin" else 1024))


def run(sizes=(1, 10, 100)) -> list[dict]:
    out = []
    for k in sizes:
        r = run_size(k)
        print(json.dumps({x: (round(v, 2) if isinstance(v, float) else v) for x, v in r.items() if x != "pipeline_s"}))
        out.append(r)
    return out
