"""Audit log and data contracts summary.

Every question, answer, role, definition used and refusal is logged. In the hosted demo the log
lives for the session (Streamlit Cloud's disk is wiped on restart); a local run also appends to
logs/audit.jsonl (git-ignored).
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

LOG = Path(__file__).resolve().parents[2] / "logs" / "audit.jsonl"
_session: list[dict] = []


def audit(ans, write_file: bool = False) -> dict:
    rec = dict(ts=dt.datetime.now().isoformat(timespec="seconds"), role=ans.role, foundation=ans.foundation,
               question=ans.question, refused=ans.refused, reason=ans.reason, definitions=ans.definitions,
               numbers=[dict(label=s.label, value=s.value, sources=s.sources[:5]) for s in ans.shown[:10]],
               number_check_passed=ans.check_passed)
    _session.append(rec)
    if write_file:
        LOG.parent.mkdir(exist_ok=True)
        with LOG.open("a") as f:
            f.write(json.dumps(rec, default=str) + "\n")
    return rec


def session_log() -> list[dict]:
    return list(_session)


def contracts_report(store) -> dict:
    """Rows blocked at the silver contracts, by reason."""
    rows = store.con.execute("SELECT source, reason, count(*) FROM silver.rejects GROUP BY 1, 2 ORDER BY 3 DESC").fetchall()
    return dict(blocked=sum(r[2] for r in rows), by_reason=[dict(source=s, reason=r[:80], rows=n) for s, r, n in rows])


def lineage(store, doc_id: str) -> dict:
    """Bronze document behind any number."""
    r = store.con.execute("SELECT doc_id, source, kind, learnt_at, as_of, text FROM bronze.documents WHERE doc_id = ?",
                          [doc_id]).fetchone()
    if not r:
        return {}
    return dict(doc_id=r[0], source=r[1], kind=r[2], learnt_at=r[3], as_of=r[4], text=r[5])
