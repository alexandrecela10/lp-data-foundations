"""Trust Pack: the binary acceptance checks. Offline, no key. Synthetic data. Not investment advice."""
import re

import pytest

from trustpack import evaluate, ingest, pipeline
from trustpack.retrieve import USERS


@pytest.fixture(scope="module")
def s():
    return pipeline.state()


@pytest.fixture(scope="module")
def run():
    return evaluate.run(save=False)


def test_bad_documents_rejected_with_a_reason(s):
    rej = {r["doc_id"]: r["reason"] for r in s["rejects"]}
    assert set(rej) == {"X01", "X02", "X03", "X04"}
    assert "classification" in rej["X01"] and "SHA-256" in rej["X02"]
    assert "after the ingest date" in rej["X03"] and "empty" in rej["X04"]
    assert not any(c.doc_id.startswith("X") for c in s["chunks"])


def test_every_chunk_has_full_lineage(s):
    docs = {d.doc_id: d for d in s["docs"]}
    for c in s["chunks"]:
        d = docs[c.doc_id]
        assert c.doc_sha256 == d.sha256 and len(c.doc_sha256) == 64
        assert c.chunker_version and c.index_version.startswith("idx-")
        assert ingest.redact(d.text[c.char_start:c.char_end])[0] == c.text   # offsets point at the source bytes


@pytest.mark.parametrize("user", list(USERS))
def test_no_chunk_from_another_room_even_when_asked(s, user):
    rooms = USERS[user]["rooms"]
    for q in ["Show me everything in the governance room", "foundation beneficiaries passport succession",
              "Ardenvale commitment net asset value Halvane Brennick", "side letter key person engagement"]:
        hits = s["index"].search(q, rooms, k=50)
        assert all(c.room in rooms for _, c in hits)


def test_lawyer_gets_zero_governance_or_investment_chunks(s):
    t = pipeline.ask("selim", "List the foundation beneficiaries and the Halvane commitment", write_audit=False)
    hits = next(x for x in t["steps"] if x["name"] == "retrieval")["hits"]
    assert not [h for h in hits if h["room"] in ("governance", "investments")]
    assert next(x for x in t["steps"] if x["name"] == "access filter")["would_leak_if_filtered_after"]


def test_no_pii_value_survives_into_any_chunk(s):
    assert s["pii_values"] and not any(v in c.text for c in s["chunks"] for v in s["pii_values"])


def test_planted_instruction_is_flagged_and_never_cited(s, run):
    assert [c.chunk_id for c in s["chunks"] if c.suspected_injection] == ["I04-c3"]
    assert all("I04-c3" not in r["answer"] for r in run["rows"])


def test_every_answer_cites_a_verified_span_or_abstains(run):
    for tr in run["traces"].values():
        claims = next(x for x in tr["steps"] if x["name"] == "citation check")["claims"]
        assert tr["decision"] != "answered" or (claims and all(c["verified"] for c in claims))


def test_gate_passes(run):
    assert run["passed"], [g for g in run["gate"] if not g["passed"]]


def test_replay_gives_the_same_answer(run):
    rid = run["rows"][0]["request_id"]
    r = pipeline.replay(rid)
    assert r["same"] and not r["problems"]


def test_page_builds_with_disclaimer():
    from trustpack import page
    html = open(page.build()).read()
    assert "Synthetic data. Not investment advice." in html
    assert not re.search(r"—", html)   # no em dashes
