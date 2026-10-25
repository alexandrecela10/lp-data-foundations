"""Langfuse tracing, pattern from Secondaries Radar: a silent no-op without
LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY, so tests and the demo run offline. Keys are never printed."""
from __future__ import annotations

import os


def enabled() -> bool:
    return bool(os.environ.get("LANGFUSE_PUBLIC_KEY") and os.environ.get("LANGFUSE_SECRET_KEY"))


def trace_answer(ans) -> str | None:
    """One trace per answer, one span per step, scores for the number check and refusal."""
    if not enabled():
        return None
    try:
        from langfuse import Langfuse
    except ImportError:
        return None
    try:
        lf = Langfuse()
        with lf.start_as_current_observation(as_type="span", name=f"answer-{ans.foundation}",
                                             input=ans.question) as root:
            for s in ans.steps:
                with lf.start_as_current_observation(as_type="span", name=s.name, input=s.input) as sp:
                    sp.update(output=s.output, metadata=dict(ms=s.ms))
            root.update(output=ans.text)
            root.score_trace(name="number_check_passed", value=1.0 if ans.check_passed else 0.0)
            root.score_trace(name="refused", value=1.0 if ans.refused else 0.0)
            tid = root.trace_id
        lf.flush()
        return tid
    except Exception:
        return None
