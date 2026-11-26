"""Trust Pack commands. Synthetic data. Not investment advice.

  python -m trustpack.cli ingest            contracts, rejects, PII redactions, chunks
  python -m trustpack.cli ask USER "QUESTION"
  python -m trustpack.cli eval              golden set, metrics, gate (exit 1 if it fails)
  python -m trustpack.cli replay REQUEST_ID      re-run and compare the trace fingerprint
  python -m trustpack.cli verify-audit          recompute the audit hash chain
  python -m trustpack.cli page              build trust_pack/site/index.html from the latest run
"""
from __future__ import annotations

import json
import sys

from . import evaluate, ingest, pipeline


def main(argv: list[str]) -> int:
    cmd = argv[0] if argv else "eval"
    if cmd == "ingest":
        s = ingest.build()
        print(f"{len(s['docs'])} documents accepted, {len(s['rejects'])} rejected, {len(s['chunks'])} chunks, "
              f"{len(s['pii_log'])} PII values redacted, index {s['index_version']}")
        for r in s["rejects"]:
            print(f"  REJECTED {r['file']}: {r['reason']}")
    elif cmd == "ask":
        tr = pipeline.ask(argv[1], argv[2])
        print(json.dumps({k: tr[k] for k in ("request_id", "decision", "answer", "citations", "online_checks")}, indent=1))
    elif cmd == "eval":
        res = evaluate.run()
        print(evaluate.report(res))
        return 0 if res["passed"] else 1
    elif cmd == "replay":
        r = pipeline.replay(argv[1])
        print(json.dumps(r, indent=1))
        return 0 if r["byte_identical"] and not r["problems"] else 1
    elif cmd == "live-eval":
        return live_eval()
    elif cmd == "calibrate":
        from . import judge
        print(json.dumps(judge.calibrate(), indent=1, default=str))
    elif cmd == "verify-audit":
        r = pipeline.verify_audit()
        print(json.dumps(r))
        return 0 if r["ok"] else 1
    elif cmd == "page":
        from . import page
        print(page.build())
    else:
        print(__doc__)
        return 2
    return 0


def live_eval() -> int:
    """Golden set through Claude, then the judge. Needs ANTHROPIC_API_KEY and TRUSTPACK_LIVE=1. Costs money."""
    from . import judge
    if not pipeline.live_enabled():
        print("Set ANTHROPIC_API_KEY and TRUSTPACK_LIVE=1 first.")
        return 2
    res = evaluate.run(save=False)
    failed = [r["id"] for r in res["rows"] if r["generator"] == "claude-error"]
    j = judge.run_judge(res)
    res["judge"] = j
    res["live_calls"] = sum(1 for r in res["rows"] if r["tokens"]["input"])
    res["live_cost_usd"] = round(sum(r["cost_usd"] for r in res["rows"]), 4)
    res["generation_failures"] = failed
    res["valid"] = not failed and not j["failed"]
    judge.make_label_sheet(res)
    slim = {k: v for k, v in res.items() if k not in ("ts", "traces")}
    evaluate.RUNS.mkdir(exist_ok=True)
    (evaluate.RUNS / f"{res['run_id']}.json").write_text(json.dumps(slim, indent=1, default=str))
    (evaluate.RUNS / "latest-live.json").write_text(json.dumps(slim, indent=1, default=str))
    print(evaluate.report(res))
    print(json.dumps({k: j[k] for k in j if k != "disagreements"}, indent=1))
    print(f"live calls {res['live_calls']}, generation cost ${res['live_cost_usd']}, valid {res['valid']}")
    return 0 if res["valid"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
