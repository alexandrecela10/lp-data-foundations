import datetime as dt

import pytest

from answerdesk import interfaces
from answerdesk.answer import DISCLAIMER


def test_dashboard_three_views(store):
    d = interfaces.dashboard(store)
    assert len(d["exposure"]) == 10 and len(d["sector"]) > 3
    assert {"net_irr", "net_tvpi", "vs_plan", "unfunded", "calls_next_12m"} <= set(d["performance"].columns)
    exp = interfaces.export_pack(d)
    assert DISCLAIMER in exp and "unfunded v2" in exp


def test_notebook_is_read_only(store):
    df = interfaces.notebook(store, "SELECT count(*) AS n FROM gold.positions")
    assert df["n"][0] > 0
    for bad in ["DROP TABLE gold.positions", "SELECT 1; DELETE FROM gold.positions"]:
        with pytest.raises(ValueError):
            interfaces.notebook(store, bad)


def test_briefing_note_has_sources_and_disclaimer(store):
    md = interfaces.briefing(store)
    assert "Brennick" in md and DISCLAIMER in md and "LET:" in md


def test_copy_text_travels_with_note_and_disclaimer(store):
    ans, _ = interfaces.chat(store, "How exposed are we to Calder Packaging?")
    txt = interfaces.copy_text(ans, note="July concern not counted")
    assert "July concern not counted" in txt and txt.strip().endswith(DISCLAIMER)
