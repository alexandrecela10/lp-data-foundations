"""Generator, sources, contracts, point in time, lineage."""
import ast
import datetime as dt
import hashlib
from pathlib import Path

from answerdesk import governance, pipeline, sources, truth, world


def test_generator_is_deterministic():
    a = sources.render(world.generate(seed=42))
    b = sources.render(world.generate(seed=42))
    h = lambda docs: hashlib.sha256("".join(d.doc_id + d.text for d in docs).encode()).hexdigest()
    assert h(a) == h(b)
    assert h(a) != h(sources.render(world.generate(seed=7)))


def test_planted_facts_exist_for_any_seed():
    for seed in (42, 7, 123):
        w = world.generate(seed=seed)
        assert w.companies["C0001"].name == "Calder Packaging Ltd"
        assert {w.spelling(m, "C0001") for m in ("M01", "M03", "M04")} == {"Calder Packaging Ltd", "Calderwick Holdings", "Calder Pack."}
        assert len(truth.exposure_routes(w, "C0001", world.TODAY)) == 5


def test_six_sources_each_with_dates(store):
    got = {s for (s,) in store.con.execute("SELECT DISTINCT source FROM bronze.documents").fetchall()}
    assert got == {"holdings", "notices", "reports", "letters", "reference", "news"}
    assert store.con.execute("SELECT count(*) FROM bronze.documents WHERE learnt_at IS NULL").fetchone()[0] == 0
    # reports arrive 40 to 90 days after their quarter end
    lag = store.con.execute("SELECT min(learnt_at - as_of), max(learnt_at - as_of) FROM bronze.documents WHERE kind = 'fund_report'").fetchone()
    assert 40 <= lag[0] and lag[1] <= 90


def test_bad_rows_are_blocked_and_logged(store):
    rep = governance.contracts_report(store)
    assert rep["blocked"] > 0
    assert all("amount format" in r["reason"] for r in rep["by_reason"])
    # every malformed notice has a corrected one, and the gold cash flows still match truth
    bad = [r[0] for r in store.con.execute("SELECT doc_id FROM silver.rejects").fetchall()]
    for b in bad:
        assert store.con.execute("SELECT count(*) FROM gold.cashflows WHERE doc_id = ?", [b + ":R"]).fetchone()[0] == 1
    assert store.con.execute("SELECT count(*) FROM gold.cashflows").fetchone()[0] == len(store.world.flows)


def test_point_in_time_write_down():
    w = world.generate()
    before = truth.exposure(w, "C0001", dt.date(2026, 9, 9))
    after = truth.exposure(w, "C0001", dt.date(2026, 9, 10))
    assert after < before * 0.8          # the 10 September letter changes the number from that day


def test_lineage_reaches_bronze(store):
    doc = store.con.execute("SELECT doc_id FROM gold.holdings LIMIT 1").fetchone()[0]
    lin = governance.lineage(store, doc)
    assert lin["source"] == "reports" and lin["text"]


def test_truth_is_independent_of_the_foundations():
    src = (Path(__file__).resolve().parents[1] / "src/answerdesk/truth.py").read_text()
    mods = set()
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.ImportFrom):
            mods.add(node.module or "")
        elif isinstance(node, ast.Import):
            mods |= {a.name for a in node.names}
    assert not any(m.split(".")[0] in ("pipeline", "semantic", "graph", "foundations", "sources", "nlu") for m in mods)
    assert mods <= {"__future__", "datetime", "dataclasses", "world"}


def test_news_has_no_numbers_in_gold(store):
    cols = [c[0] for c in store.con.execute("DESCRIBE gold.news").fetchall()]
    assert cols == ["doc_id", "ts", "text"]
