"""One command to rebuild everything.

    python -m answerdesk.cli all        # build, offline eval, held-out eval, scale runs (writes evals/results/)
    python -m answerdesk.cli build      # generator -> bronze -> silver -> gold, prints counts
    python -m answerdesk.cli eval       # offline eval on seed 42 and the held-out world (seed 7, noisy names)
    python -m answerdesk.cli scale      # 1x, 10x, 100x timings
    python -m answerdesk.cli live       # live eval with claude-sonnet-5-5 (needs ANTHROPIC_API_KEY; costs money)
    python -m answerdesk.cli ask "How exposed are we to Calder Packaging?" [--arm D] [--role analyst]
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from . import evals, pipeline


def _print_summary(res):
    for arm, s in res["summary"].items():
        print(f"{arm:6} correct {s['correct']:2}/{s['of']}  (R1 {s['request_1']}, R2 {s['request_2']}, R3 {s['request_3']})  "
              f"wrong but sourced {s['wrong_but_sourced']:2}  refusals {s['correct_refusals']}/{s['refusal_traps']}  "
              f"median time to send {s['median_time_to_send_s'] or 0:.0f}s")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="answerdesk")
    ap.add_argument("cmd", choices=["all", "build", "eval", "scale", "live", "ask"])
    ap.add_argument("question", nargs="?")
    ap.add_argument("--arm", default="D")
    ap.add_argument("--role", default="analyst")
    a = ap.parse_args(argv)
    if a.cmd == "build":
        st = pipeline.build()
        print(json.dumps(dict(timings=st.timings, counts=st.counts), indent=1, default=str))
    if a.cmd in ("eval", "all"):
        res = evals.run(seed=42)
        print("saved", evals.save(res, "offline-seed42.json"))
        _print_summary(res)
        held = evals.run(seed=7, noisy=True, reruns=1)
        print("saved", evals.save(held, "offline-heldout-seed7-noisy.json"))
        _print_summary(held)
    if a.cmd in ("scale", "all"):
        from . import scale
        rs = scale.run()
        p = evals.RESULTS / "scale.json"
        p.write_text(json.dumps(rs, indent=1, default=str))
        print("saved", p)
    if a.cmd == "live":
        if not os.environ.get("ANTHROPIC_API_KEY"):
            sys.exit("ANTHROPIC_API_KEY is not set. Live results stay 'not yet run'.")
        os.environ["ANSWERDESK_LIVE"] = "1"
        from . import llm
        print(llm.NOTICE)
        res = evals.run(seed=42, reruns=2)
        res["meta"]["mode"] = f"live ({llm.MODEL})"
        billed = res["meta"]["all_passes"]
        # a live call that failed fell back offline; one such answer makes the run unfair, so it doesn't count
        res["meta"]["valid"] = billed["live_failures"] == 0
        print("saved", evals.save(res, "live-claude-sonnet-5-5.json"))
        _print_summary(res)
        print(f"passes {billed['passes']}  calls {billed['llm_calls']}  cost ${billed['cost_usd']}  "
              f"live failures {billed['live_failures']}")
        if not res["meta"]["valid"]:
            print("INVALID: some live calls failed and fell back offline. Examples:", *billed["failure_examples"], sep="\n  ")
            sys.exit(1)
    if a.cmd == "ask":
        from .interfaces import chat
        st = pipeline.build()
        ans, _ = chat(st, a.question, a.role, a.arm)
        print(ans.text)


if __name__ == "__main__":
    main()
