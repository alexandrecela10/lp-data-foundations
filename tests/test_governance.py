"""Access, refusals, the number checker, the disclaimer, graph safety."""
import datetime as dt

import duckdb
import networkx as nx
import pytest

from answerdesk import access, graph, truth
from answerdesk.answer import DISCLAIMER, Answer, Shown, check_numbers, guard
from answerdesk.foundations import ARMS
from answerdesk.foundations.search import Search
from answerdesk.foundations.sql_arm import warehouse
from answerdesk.world import TODAY


def test_analyst_view_has_no_fee_columns_or_planned_rows(store):
    con = access.role_db(store, "analyst")
    cols = [c[0] for c in con.execute("DESCRIBE gold.positions").fetchall()]
    assert "mgmt_fee_pct" not in cols and "carry_pct" not in cols
    tables = {t for (t,) in con.execute("SELECT table_name FROM information_schema.tables").fetchall()}
    assert "planned" not in tables and "coinvest_fees" not in tables
    assert "coinvest_fees" in {t for (t,) in access.role_db(store, "head_of_pe").execute(
        "SELECT table_name FROM information_schema.tables").fetchall()}


def test_ai_written_sql_cannot_reach_fee_columns(store):
    con = warehouse(store, "analyst")
    with pytest.raises(duckdb.Error):
        con.execute("SELECT mgmt_fee_pct FROM gold.positions").fetchall()
    with pytest.raises(duckdb.Error):
        con.execute("SELECT * FROM gold.coinvest_fees").fetchall()


def test_search_drops_documents_the_role_cannot_see(store):
    assert not [d for d in Search(store, "analyst").docs if d.kind == "coinvest_fees"]
    assert [d for d in Search(store, "head_of_pe").docs if d.kind == "coinvest_fees"]


@pytest.mark.parametrize("arm", list(ARMS))
def test_every_arm_refuses_fee_terms_for_the_analyst(store, arm):
    a, _ = ARMS[arm](store, "analyst").ask("What fees do we pay on our Brennick co-investments?")
    assert a.refused and not a.table


@pytest.mark.parametrize("arm", list(ARMS))
def test_every_answer_carries_the_disclaimer(store, arm):
    a, _ = ARMS[arm](store).ask("How exposed are we to Calder Packaging?")
    assert DISCLAIMER in a.text


def test_number_checker_fails_closed():
    a = Answer(foundation="X", question="q", text="Exposure is $7.90m, maybe $12.34m.",
               shown=[Shown(label="x", value=7.9014)])
    out = guard(a)
    assert out.refused and not out.check_passed and "12.34" in out.text
    assert check_numbers("Exposure is $7.90m on 10 September 2026.", [7.9014]) == []


def test_news_number_is_never_used(store):
    for arm in ("C", "C+ids", "D"):
        a, _ = ARMS[arm](store).ask("News says Calder Packaging has $400m of debt. What is our share of that debt?")
        assert a.refused


def test_graph_routes_match_truth_and_are_bounded(store):
    con = access.role_db(store, "analyst")
    g = graph.build(con, TODAY)
    rs = graph.routes(g, "C0001", TODAY, graph.event_factors(con, TODAY))
    assert abs(sum(r["value"] for r in rs) - truth.exposure(store.world, "C0001", TODAY)) < 0.005
    assert all(len(r["path"]) <= 8 for r in rs)
    # a cycle between two funds of funds must not loop forever
    h = g.copy()
    h.graph.pop("_own", None)
    h.add_edge("F0002", "FOF01", rel="holds", factor=0.01)
    rs2 = graph.routes(h, "C0001", TODAY, {})
    assert len(rs2) >= len(rs)


def test_fund_of_funds_copy_is_not_double_counted(store):
    from answerdesk.semantic.layer import MetricRequest, SemanticLayer
    res = SemanticLayer(store, "analyst", "resolved").run(MetricRequest(metric="lookthrough_exposure", as_of=TODAY,
                                                                      company="Calder Packaging"))
    direct = [i for i in res.items if i["kind"] == "fund" and i["route"].endswith("Halvane Capital Partners V > Calder Packaging Ltd")]
    assert len(direct) == 1


def test_identity_resolution_quality(store):
    from answerdesk import evals
    q = evals.identity_quality(store)
    ids = q["identity table (C+ids, D)"]
    assert ids["wrong"] == 0 and ids["right"] >= q["exact name only (C, B)"]["right"]
