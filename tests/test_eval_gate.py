"""Eval gate (a regression gate on the build, labelled a mechanism test; not the ranking).

Blocks the build if the winning combination breaks: any non-trap question wrong for D, any
refusal trap answered, any wrong number shown as sourced by D, or a rerun that changes an answer.
"""
from answerdesk import questions


def test_sixty_questions_twenty_per_request(qs):
    assert len(qs) == 60
    assert [sum(1 for q in qs.values() if q.request == r) for r in (1, 2, 3)] == [20, 20, 20]
    traps = {t for q in qs.values() for t in q.traps}
    assert {"spelling", "role", "no_definition", "point_in_time", "follow_up", "news"} <= traps


def test_d_answers_every_question(offline_results):
    s = offline_results["summary"]["D"]
    assert s["correct"] == 60, [r["qid"] for r in offline_results["rows"] if r["arm"] == "D" and not r["correct"]]


def test_d_shows_no_wrong_sourced_number(offline_results):
    assert offline_results["summary"]["D"]["wrong_but_sourced"] == 0


def test_governed_arms_refuse_every_refusal_trap(offline_results):
    for arm in ("C", "C+ids", "D"):
        s = offline_results["summary"][arm]
        assert s["correct_refusals"] == s["refusal_traps"]


def test_same_answer_on_rerun(offline_results):
    assert all(v == 1.0 for v in offline_results["same_answer_on_rerun"].values())


def test_governed_arms_same_answer_on_rephrase(offline_results):
    for arm in ("C+ids", "D"):
        assert offline_results["same_answer_on_rephrase"][arm] == 1.0


def test_held_out_world_still_passes():
    from answerdesk import evals
    held = evals.run(seed=7, noisy=True, reruns=1)
    assert held["summary"]["D"]["correct"] >= 57          # held-out: noisy names never tuned on
    assert held["summary"]["D"]["wrong_but_sourced"] <= 1
