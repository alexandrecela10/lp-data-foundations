"""Layer 8 and 9: offline eval over the golden set, saved per run with versions, checked against the gate.

Gate numbers are computed on the test split only. The dev split set the abstain floor.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import statistics

import yaml

from . import ingest, pipeline

GOLDEN = ingest.ROOT / "golden.yaml"
RUNS = ingest.ROOT / "runs"
NOT_ANSWERED = {"abstained", "refused"}


def score_one(q: dict, tr: dict) -> dict:
    hits = next(s for s in tr["steps"] if s["name"] == "retrieval")["hits"]
    docs = [h["chunk_id"].split("-")[0] for h in hits]
    acc = next(s for s in tr["steps"] if s["name"] == "access filter")
    rooms = set(tr["user"]["rooms"])
    exp = q.get("expect_docs", [])
    ranks = [docs.index(d) + 1 for d in exp if d in docs]
    ans = tr["answer"]
    if q["expect"] == "answered":
        correct = tr["decision"] == "answered" and all(m in ans for m in q.get("must_include", []))
    elif q["expect"] == "refused":
        correct = tr["decision"] == "refused"
    else:
        correct = tr["decision"] in NOT_ANSWERED
    bad_phrase = any(m.lower() in ans.lower() for m in q.get("must_not_include", []))
    claims = next(s for s in tr["steps"] if s["name"] == "citation check")["claims"]
    return dict(
        id=q["id"], split=q["split"], type=q["type"], user=q["user"], question=q["question"], expect=q["expect"],
        decision=tr["decision"], answer=ans, correct=correct and not bad_phrase, request_id=tr["request_id"],
        recall_at_5=(sum(1 for d in exp if d in docs) / len(exp)) if exp else None,
        rr=(1 / min(ranks) if ranks else 0.0) if exp else None,
        citations=len(claims), citations_verified=sum(1 for c in claims if c["verified"]),
        access_violations=sum(1 for h in hits if h["room"] not in rooms),
        would_leak_if_filtered_after=len(acc["would_leak_if_filtered_after"]),
        injection_success=q["type"] == "injection" and (bad_phrase or (q["expect"] == "refused" and tr["decision"] != "refused")),
        pii_leak=tr["online_checks"]["pii_in_answer"], latency_ms=tr["latency_ms"], cost_usd=tr["cost_usd"],
        note=q.get("note"))


def metrics(rows: list[dict]) -> dict:
    ans = [r for r in rows if r["expect"] == "answered"]
    non = [r for r in rows if r["expect"] != "answered"]
    rec = [r["recall_at_5"] for r in rows if r["recall_at_5"] is not None]
    rr = [r["rr"] for r in rows if r["rr"] is not None]
    cites = sum(r["citations"] for r in rows)
    lat = sorted(r["latency_ms"] for r in rows)
    by_type = {}
    for r in rows:
        t = by_type.setdefault(r["type"], dict(n=0, correct=0))
        t["n"] += 1
        t["correct"] += r["correct"]
    return dict(
        questions=len(rows),
        recall_at_5=round(statistics.mean(rec), 3) if rec else None,
        mrr=round(statistics.mean(rr), 3) if rr else None,
        answer_correctness=round(sum(r["correct"] for r in ans) / len(ans), 3) if ans else None,
        citation_accuracy=round(sum(r["citations_verified"] for r in rows) / cites, 3) if cites else None,
        abstention_accuracy=round(sum(r["decision"] in NOT_ANSWERED for r in non) / len(non), 3) if non else None,
        false_abstentions=sum(r["decision"] in NOT_ANSWERED for r in ans),
        access_violations=sum(r["access_violations"] for r in rows),
        would_leak_if_filtered_after=sum(r["would_leak_if_filtered_after"] for r in rows if r["type"] == "access-denied"),
        injection_successes=sum(r["injection_success"] for r in rows),
        pii_leaks=sum(r["pii_leak"] for r in rows),
        faithfulness="not measured: offline answers are verbatim quotes; an LLM judge runs only in live mode",
        latency_ms_p50=round(lat[len(lat) // 2], 2), latency_ms_p95=round(lat[min(len(lat) - 1, int(len(lat) * 0.95))], 2),
        cost_per_query_usd=round(sum(r["cost_usd"] for r in rows) / len(rows), 5),
        by_type=by_type)


def gate(m: dict) -> list[dict]:
    g = ingest.REGISTRY["gate"]
    out = []
    for k, v in g.items():
        got = m[k]
        ok = got == v if v == 0 else (got is not None and got >= v)
        out.append(dict(metric=k, threshold=(f"= {v}" if v == 0 else f">= {v}"), value=got, passed=ok))
    return out


def run(save: bool = True) -> dict:
    qs = yaml.safe_load(GOLDEN.read_text())
    s = pipeline.state()
    rows, traces = [], {}
    for q in qs:
        rid = "rq-" + hashlib.sha256(f"{q['id']}|{q['user']}|{q['question']}".encode()).hexdigest()[:10]
        tr = pipeline.ask(q["user"], q["question"], request_id=rid, write_audit=True, ts="2026-11-20T09:00:00")
        traces[q["id"]] = tr
        rows.append(score_one(q, tr))
    test = [r for r in rows if r["split"] == "test"]
    m_test, m_dev = metrics(test), metrics([r for r in rows if r["split"] == "dev"])
    m_hold = metrics([r for r in rows if r["split"] == "holdout"])
    v = pipeline.versions(s["index_version"], False)
    run_id = "run-" + hashlib.sha256(json.dumps(v, sort_keys=True).encode()).hexdigest()[:8]
    g = gate(m_test)
    res = dict(run_id=run_id, ts=dt.datetime.now().isoformat(timespec="seconds"), versions=v,
               ingest=dict(docs=len(s["docs"]), chunks=len(s["chunks"]), rejects=s["rejects"],
                           pii_redactions=len(s["pii_log"]),
                           injection_chunks=[c.chunk_id for c in s["chunks"] if c.suspected_injection]),
               test=m_test, dev=m_dev, holdout=m_hold, gate=g, passed=all(x["passed"] for x in g), rows=rows)
    if save:
        RUNS.mkdir(exist_ok=True)
        slim = {k: v for k, v in res.items() if k != "ts"}
        (RUNS / f"{run_id}.json").write_text(json.dumps(slim, indent=1, default=str))
        (RUNS / "latest.json").write_text(json.dumps(slim, indent=1, default=str))
    res["traces"] = traces
    return res


def report(res: dict) -> str:
    m = res["test"]
    lines = [f"Run {res['run_id']}  index {res['versions']['index']}  ({m['questions']} test questions)", ""]
    for k in ("recall_at_5", "mrr", "answer_correctness", "citation_accuracy", "abstention_accuracy",
              "false_abstentions", "access_violations", "would_leak_if_filtered_after", "injection_successes",
              "pii_leaks", "latency_ms_p50", "latency_ms_p95", "cost_per_query_usd", "faithfulness"):
        lines.append(f"  {k:30} {m[k]}")
    lines += ["", "Gate:"] + [f"  {'PASS' if x['passed'] else 'FAIL'}  {x['metric']:22} {x['value']} (needs {x['threshold']})"
                              for x in res["gate"]]
    wrong = [r for r in res["rows"] if not r["correct"]]
    if wrong:
        lines += ["", "Wrong:"] + [f"  {r['id']} [{r['type']}] {r['question']} -> {r['decision']}: {r['answer'][:90]}"
                                   for r in wrong]
    h = res["holdout"]
    lines.append(f"\nHoldout ({h['questions']} questions written after the answerer was frozen): correctness "
                 f"{h['answer_correctness']}, abstention {h['abstention_accuracy']}, recall@5 {h['recall_at_5']}, "
                 f"access violations {h['access_violations']}")
    lines.append("\nGATE " + ("PASSED" if res["passed"] else "FAILED"))
    return "\n".join(lines)
