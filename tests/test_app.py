"""The Streamlit demo, driven by AppTest with no key."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / "app.py")


@pytest.fixture(scope="module")
def at():
    a = AppTest.from_file(APP, default_timeout=120)
    a.run()
    return a


def test_runs_without_errors(at):
    assert not at.exception, at.exception


def test_value_statement_first_and_tabs_name_the_tool(at):
    assert at.title[0].value == "Portfolio Answer Desk"
    assert "correct, sourced answer" in at.markdown[0].value
    labels = [t.label for t in at.tabs]
    for name in ["Portfolio chat", "Committee pack", "Manager briefing", "SQL notebook", "Foundation test",
                 "How it works", "Under the hood"]:
        assert name in labels


def test_disclaimer_shown(at):
    assert any("Synthetic data. Not investment advice." in c.value for c in at.caption)


def test_calder_answer_and_routes(at):
    assert any("For the CIO" in m.value and "5 routes" in m.value for m in at.markdown)


def test_refusal_card_for_fee_question():
    a = AppTest.from_file(APP, default_timeout=120)
    a.run()
    a.text_input(key="question").set_value("What fees do we pay on the Calderwick Holdings co-investment?").run()
    assert not a.exception
    assert any("Not answered" in e.value for e in a.error)


def test_graph_walk_steps():
    a = AppTest.from_file(APP, default_timeout=120)
    a.run()
    a.button(key="edu_next").click().run()
    assert not a.exception
    assert any("Hop 1 of" in c.value for c in a.caption)


def test_send_is_logged():
    a = AppTest.from_file(APP, default_timeout=120)
    a.run()
    a.button(key="send").click().run()
    assert any("Logged as sent" in s.value for s in a.success)


def test_head_of_pe_sees_fees():
    a = AppTest.from_file(APP, default_timeout=120)
    a.run()
    a.sidebar.radio(key="role").set_value("head_of_pe").run()
    a.text_input(key="question").set_value("What fees do we pay on our Brennick co-investments?").run()
    assert not a.exception
    assert not any("Not answered" in e.value for e in a.error)
