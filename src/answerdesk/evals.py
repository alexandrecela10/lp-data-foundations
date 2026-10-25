"""Evaluation: run every arm on the 60 questions, score against known answers, measure.

Main metric: time until Sara has a correct, sourced answer she would send = answer latency +
checking time (answer.py, ASSUMED model). A wrong answer is a fail, however fast. For an expected
time per question, a fail costs a manual fallback of 2 hours (ASSUMED).
"""
from __future__ import annotations

import datetime as dt
import json
import statistics
import subprocess
import time
from pathlib import Path

from . import pipeline, questions
from .answer import CHECK, Answer
from .foundations import ARMS, LABELS
from .pipeline import normalise

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "evals" / "results"
MANUAL_FALLBACK_S = 2 * 3600        # ASSUMED
ARM_ORDER = ["A", "B", "C", "C+ids", "D"]


def _norm_set(xs, expected):
    managerish = all(("Partners" in e or "Ventures" in e) and not e.split()[-1] in
                     ("I", "II", "III", "IV", "V", "VI", "VII") for e in expected) if expected else False
    if managerish:
        return {normalise(x).split()[0] for x in xs if x}
    return {normalise(x) if not str(x).startswith("LET:") else x for x in xs if x}


def score(q: questions.Question, a: Answer) -> dict:
    exp = q.expected
    out = dict(correct=False, refusal_expected=q.kind == "refusal", refused=a.refused, detail="")
    if q.kind == "refusal":
        out["correct"] = a.refused
        out["detail"] = "refused" if a.refused else "answered instead of refusing"
        return out
    if a.refused:
        out["detail"] = f"refused: {a.reason[:80]}"
        return out
    if q.kind == "number":
        ok = a.value is not None and (abs(a.value - exp) <= max(q.tol * abs(exp), 0.01))
        routes_ok = q.routes is None or set(a.route_sigs) == set(q.routes)
        out["correct"] = ok and routes_ok
        out["detail"] = (f"value {a.value if a.value is None else round(a.value, 4)} vs {round(exp, 4)}"
                         + ("" if routes_ok else f"; routes {len(a.route_sigs)} vs {len(q.routes)}"))
    elif q.kind == "set":
        got, want = _norm_set(a.items, exp), _norm_set(exp, exp)
        out["correct"] = got == want
        out["detail"] = f"found {len(got & want)}/{len(want)}, extra {len(got - want)}"
    elif q.kind == "date":
        out["correct"] = a.date == exp
        out["detail"] = f"{a.date} vs {exp}"
    elif q.kind == "table":
        got = {normalise(k): v for k, v in a.table.items()}
        want = {normalise(k): v for k, v in exp.items()}
        ok = set(got) == set(want) and all(got[k] is not None and want[k] is not None and abs(got[k] - want[k]) <= q.tol
                                          for k in want)
        out["correct"] = ok
        bad = [k for k in want if k not in got or got[k] is None or abs(got[k] - want[k]) > q.tol]
        out["detail"] = f"{len(want) - len(bad)}/{len(want)} rows within {q.tol}"
    elif q.kind == "composite":
        c = a.composite or {}
        ok_c = c.get("commitment") is not None and abs(c["commitment"] - exp["commitment"]) <= 0.01
        ok_f = _norm_set(c.get("funds", []), exp["funds"]) == _norm_set(exp["funds"], exp["funds"])
        ok_i = set(c.get("issues", [])) == set(exp["issues"])
        out["correct"] = ok_c and ok_f and ok_i
        out["detail"] = f"commitment {'ok' if ok_c else 'wrong'}, funds {'ok' if ok_f else 'wrong'}, issues {len(set(c.get('issues', [])) & set(exp['issues']))}/{len(exp['issues'])}"
    return out


def fingerprint(a: Answer) -> str:
    return json.dumps(dict(v=None if a.value is None else round(a.value, 6), i=sorted(a.items), d=str(a.date),
                           t={k: None if v is None else round(v, 6) for k, v in sorted(a.table.items())},
                           r=a.refused, s=sorted(a.route_sigs)), sort_keys=True)


def run_arm(store, arm: str, qs: list) -> list[dict]:
    rows = []
    prev_intent = {}
    agents = {}
    for q in qs:
        key = (arm, q.role)
        if key not in agents:
            agents[key] = ARMS[arm](store, q.role)
        prev = prev_intent.get(q.follows) if q.follows else None
        a, it = agents[key].ask(q.text, prev)
        prev_intent[q.id] = it
        s = score(q, a)
        sourced_shown = any(x.sourced for x in a.shown) or any(a.item_sources.values())
        check = a.checking_s()
        rows.append(dict(
            arm=arm, qid=q.id, request=q.request, question=q.text, role=q.role, traps=list(q.traps), kind=q.kind,
            correct=s["correct"], detail=s["detail"], refused=a.refused, refusal_expected=s["refusal_expected"],
            wrong_but_sourced=(not s["correct"]) and (not a.refused) and sourced_shown,
            latency_s=a.latency_s, compute_s=a.compute_s, checking_s=check,
            time_to_send_s=(a.latency_s + check) if s["correct"] else None,
            llm_calls=a.llm_calls, prompt_tokens=a.tokens_in, cost_usd=a.cost_usd,
            numbers_shown=len(a.shown), sourced_numbers=sum(1 for x in a.shown if x.sourced),
            defined_numbers=sum(1 for x in a.shown if x.defined), check_passed=a.check_passed,
            data_age_days=(min((x.as_of for x in a.shown if x.as_of), default=None) and
                           (a.as_of - min(x.as_of for x in a.shown if x.as_of)).days),
            answer=a.text[:600], fingerprint=fingerprint(a),
            shown=[dict(sourced=x.sourced, defined=x.defined) for x in a.shown],
            items=len(a.items), item_sourced=sum(1 for i in a.items if a.item_sources.get(i)),
            live_failures=a.live_failures))
    return rows


def pctl(xs, p):
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return None
    k = (len(xs) - 1) * p
    lo, hi = int(k), min(int(k) + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (k - lo)


def recheck_time(r: dict, k: dict, recheck_share: float) -> float:
    """Checking time under a different model: k overrides, and a share of sourced numbers rechecked by hand."""
    if r["refused"]:
        return k["read"] + k["forward_refusal"]
    t = k["read"]
    for s in r["shown"]:
        base = k["sourced_defined"] if s["sourced"] and s["defined"] else (k["sourced"] if s["sourced"] else k["by_hand"])
        t += base if not s["sourced"] else (1 - recheck_share) * base + recheck_share * k["by_hand"]
    t += r["item_sourced"] * k["item_sourced"] + (r["items"] - r["item_sourced"]) * k["item_unsourced"]
    return t


def summarise(rows: list[dict]) -> dict:
    out = {}
    for arm in ARM_ORDER:
        rs = [r for r in rows if r["arm"] == arm]
        if not rs:
            continue
        by_req = {f"request_{n}": sum(r["correct"] for r in rs if r["request"] == n) for n in (1, 2, 3)}
        tts = [r["time_to_send_s"] for r in rs if r["time_to_send_s"] is not None]
        tts_r1 = [r["time_to_send_s"] for r in rs if r["time_to_send_s"] is not None and r["request"] == 1]
        exp_time = [r["time_to_send_s"] if r["time_to_send_s"] is not None else MANUAL_FALLBACK_S for r in rs]
        ref_exp = [r for r in rs if r["refusal_expected"]]
        out[arm] = dict(
            label=LABELS[arm], correct=sum(r["correct"] for r in rs), of=len(rs), **by_req,
            wrong_but_sourced=sum(r["wrong_but_sourced"] for r in rs),
            correct_refusals=sum(r["refused"] for r in ref_exp), refusal_traps=len(ref_exp),
            false_refusals=sum(1 for r in rs if r["refused"] and not r["refusal_expected"]),
            median_time_to_send_s=pctl(tts, 0.5), p95_time_to_send_s=pctl(tts, 0.95),
            median_time_to_send_r1_s=pctl(tts_r1, 0.5),
            expected_time_per_question_s=statistics.mean(exp_time),
            latency_p50_s=pctl([r["latency_s"] for r in rs], 0.5), latency_p95_s=pctl([r["latency_s"] for r in rs], 0.95),
            compute_p50_ms=1000 * pctl([r["compute_s"] for r in rs], 0.5),
            compute_p95_ms=1000 * pctl([r["compute_s"] for r in rs], 0.95),
            cost_per_answer_usd=statistics.mean(r["cost_usd"] for r in rs),
            prompt_tokens_mean=statistics.mean(r["prompt_tokens"] for r in rs),
            sourced_share=(sum(r["sourced_numbers"] for r in rs) / max(1, sum(r["numbers_shown"] for r in rs))),
            median_data_age_days=pctl([r["data_age_days"] for r in rs], 0.5),
            number_check_failures=sum(1 for r in rs if not r["check_passed"]),
        )
    return out


def sensitivity(rows: list[dict]) -> list[dict]:
    variants = [("base", {}, 0.0), ("half the per-number times", "half", 0.0), ("double", "double", 0.0),
                ("50% of sourced numbers rechecked by hand", {}, 0.5), ("all sourced numbers rechecked", {}, 1.0)]
    out = []
    for name, mod, share in variants:
        k = dict(CHECK)
        if mod == "half":
            k = {x: v / 2 if x != "read" else v for x, v in k.items()}
        elif mod == "double":
            k = {x: v * 2 if x != "read" else v for x, v in k.items()}
        med = {}
        for arm in ARM_ORDER:
            ts = [r["latency_s"] + recheck_time(r, k, share) for r in rows if r["arm"] == arm and r["correct"]]
            med[arm] = pctl(ts, 0.5)
        rank = sorted((a for a in med if med[a] is not None), key=lambda a: med[a])
        out.append(dict(variant=name, median_s=med, ranking=rank))
    return out


def identity_quality(store) -> dict:
    """How well each arm's company matching does against the generator's truth."""
    w = store.world
    truth = {}
    for f in w.funds.values():
        for cid in f.weights:
            truth[w.spelling(f.manager_id, cid)] = cid
    for c in w.coinvests.values():
        nm = c.name_on_docs.split(" (")[0]
        tid = c.company_id
        kids = [k.id for k in w.companies.values() if k.parent_id == tid]
        truth[nm] = kids[0] if len(kids) == 1 and w.companies[tid].is_holdco else tid
    for k, v in list(truth.items()):
        if w.companies[v].is_holdco:
            kids = [c.id for c in w.companies.values() if c.parent_id == v]
            if len(kids) == 1:
                truth[k] = kids[0]
    rows = store.con.execute("SELECT name_reported, company_id_exact, company_id, status FROM gold.identity").fetchall()
    res = {}
    for label, col in (("exact name only (C, B)", 1), ("identity table (C+ids, D)", 2)):
        right = wrong = missed = 0
        for r in rows:
            t = truth.get(r[0])
            if t is None:
                continue
            got = r[col] if (col == 1 or r[3] == "accepted") else None
            if got is None:
                missed += 1
            elif got == t:
                right += 1
            else:
                wrong += 1
        res[label] = dict(right=right, wrong=wrong, missed=missed, names=right + wrong + missed)
    return res


def build_effort() -> dict:
    src = ROOT / "src" / "answerdesk"

    def loc(*paths):
        return sum(sum(1 for ln in (src / p).read_text().splitlines() if ln.strip() and not ln.strip().startswith("#"))
                   for p in paths)
    shared = loc("world.py", "sources.py", "pipeline.py", "contracts.py", "access.py", "nlu.py", "answer.py")
    return {
        "shared (generator, sources, pipeline, access, question reader)": dict(loc=shared),
        "A": dict(loc=loc("foundations/docs_arm.py", "foundations/search.py"), moving_parts=["search index", "AI reader"]),
        "B": dict(loc=loc("foundations/sql_arm.py"), moving_parts=["warehouse tables", "AI SQL writer", "SQL runner"]),
        "C": dict(loc=loc("semantic/layer.py", "semantic/fin.py", "semantic/metrics.yaml", "foundations/semantic_arms.py"),
                  moving_parts=["warehouse tables", "metric registry", "semantic compiler", "AI metric picker"]),
        "C+ids": dict(loc=loc("semantic/layer.py", "semantic/fin.py", "semantic/metrics.yaml", "foundations/semantic_arms.py"),
                      moving_parts=["warehouse tables", "identity table", "metric registry", "semantic compiler", "AI metric picker"]),
        "D": dict(loc=loc("semantic/layer.py", "semantic/fin.py", "semantic/metrics.yaml", "foundations/semantic_arms.py",
                          "graph.py", "foundations/search.py"),
                  moving_parts=["warehouse tables", "identity table", "metric registry", "semantic compiler", "graph",
                                "letter search", "AI router and picker"]),
    }


def run(seed: int = 42, noisy: bool = False, reruns: int = 2) -> dict:
    t0 = time.perf_counter()
    store = pipeline.build(seed=seed, noisy=noisy)
    qs = questions.build(store.world)
    rows = []
    for arm in ARM_ORDER:
        rows += run_arm(store, arm, qs)
    same = {}
    passes = [rows]  # reruns = total passes over the 60 questions; the first pass is the one scored
    for _ in range(reruns - 1):
        passes.append([r for arm in ARM_ORDER for r in run_arm(store, arm, qs)])
    if len(passes) > 1:
        for arm in ARM_ORDER:
            rs = [r for r in rows if r["arm"] == arm]
            fps = [{r["qid"]: r["fingerprint"] for r in p if r["arm"] == arm} for p in passes[1:]]
            same[arm] = sum(all(fp[r["qid"]] == r["fingerprint"] for fp in fps) for r in rs) / len(rs)
    every = [r for p in passes for r in p]
    billed = dict(passes=len(passes), llm_calls=sum(r["llm_calls"] for r in every),
                  cost_usd=round(sum(r["cost_usd"] or 0 for r in every), 2),
                  live_failures=sum(len(r["live_failures"]) for r in every),
                  failure_examples=sorted({f for r in every for f in r["live_failures"]})[:5])
    rephrase_groups = [["R1-01", "R1-02"], ["R2-03", "R2-11", "R2-12"]]
    consistency = {}
    for arm in ARM_ORDER:
        fps = {r["qid"]: r["fingerprint"] for r in rows if r["arm"] == arm}
        consistency[arm] = sum(len({fps[q] for q in g}) == 1 for g in rephrase_groups) / len(rephrase_groups)
    try:
        commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    except Exception:
        commit = ""
    return dict(
        meta=dict(seed=seed, noisy=noisy, mode="offline (deterministic stand-ins for the AI)", model_live="claude-sonnet-5-5",
                  run_at=dt.datetime.now().isoformat(timespec="seconds"), commit=commit, questions=len(qs),
                  pipeline_seconds=store.timings, documents=store.counts,
                  checking_time_model=CHECK, manual_fallback_s=MANUAL_FALLBACK_S,
                  assumed_seconds_per_ai_call=3.0, wall_seconds=time.perf_counter() - t0, all_passes=billed),
        summary=summarise(rows), same_answer_on_rerun=same, same_answer_on_rephrase=consistency,
        sensitivity=sensitivity(rows), identity=identity_quality(store), build_effort=build_effort(), rows=rows)


def save(res: dict, name: str) -> Path:
    RESULTS.mkdir(parents=True, exist_ok=True)
    p = RESULTS / name
    p.write_text(json.dumps(res, indent=1, default=str))
    return p
