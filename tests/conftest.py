import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
os.environ.pop("ANSWERDESK_LIVE", None)          # tests never call a model

from answerdesk import pipeline, questions  # noqa: E402


@pytest.fixture(scope="session")
def store():
    return pipeline.build(seed=42)


@pytest.fixture(scope="session")
def qs(store):
    return {q.id: q for q in questions.build(store.world)}


@pytest.fixture(scope="session")
def offline_results():
    from answerdesk import evals
    return evals.run(seed=42, reruns=2)
