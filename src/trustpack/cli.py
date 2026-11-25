"""Trust Pack commands. Synthetic data. Not investment advice.

  python -m trustpack.cli ingest            contracts, rejects, PII redactions, chunks
  python -m trustpack.cli ask USER "QUESTION"
  python -m trustpack.cli eval              golden set, metrics, gate (exit 1 if it fails)
  python -m trustpack.cli replay REQUEST_ID
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
        return 0 if r["same"] and not r["problems"] else 1
    elif cmd == "page":
        from . import page
        print(page.build())
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
