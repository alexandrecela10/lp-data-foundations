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
    assert r["byte_identical"] and r["same"] and not r["problems"]


def test_page_builds_with_disclaimer():
    from trustpack import page
    html = open(page.build()).read()
    assert "Synthetic data. Not investment advice." in html
    assert not re.search(r"—", html)   # no em dashes


def test_browser_engine_matches_python(tmp_path):
    """The page's JS engine must give the same decision and answer as Python on every case it can be asked."""
    import json
    import shutil
    import subprocess

    import yaml

    from trustpack import page
    if not shutil.which("node"):
        pytest.skip("node not installed")
    s = pipeline.state()
    qs = [q["question"] for q in yaml.safe_load(evaluate.GOLDEN.read_text())]
    qs += [a["question"] for a in page.RED_TEAM] + page.DEMO_QUESTIONS
    cases = [(u, q) for q in qs for u in USERS]
    (tmp_path / "data.json").write_text(json.dumps(dict(engine=page.engine_data(s), cases=cases), default=str))
    js = ("const E=require(process.argv[1]);const d=require(process.argv[2]);globalThis.performance??=require('perf_hooks').performance;"
          "const e=E(d.engine);console.log(JSON.stringify(d.cases.map(([u,q])=>{const t=e.ask(u,q);return [t.decision,t.answer,t.stopped_at]})))")
    out = subprocess.run(["node", "-e", js, str(page.ENGINE), str(tmp_path / "data.json")], capture_output=True, text=True, check=True)
    got = json.loads(out.stdout)
    diffs = []
    for (u, q), g in zip(cases, got):
        t = pipeline.ask(u, q, write_audit=False)
        if [t["decision"], t["answer"], t["stopped_at"]] != g:
            diffs.append((u, q, t["answer"][:60], g[1][:60]))
    assert len(cases) > 250 and not diffs, diffs[:5]


def test_audit_chain_detects_an_edited_line(tmp_path):
    log = tmp_path / "audit.jsonl"
    for q in ["What is the net IRR of Halvane Growth Fund III?", "Should we exit the Brennick fund?"]:
        pipeline.audit(pipeline.ask("priya", q, write_audit=False), log=log)
    assert pipeline.verify_audit(log)["ok"]
    lines = log.read_text().splitlines()
    lines[0] = lines[0].replace("priya", "karim")
    log.write_text("\n".join(lines) + "\n")
    assert pipeline.verify_audit(log) == dict(ok=False, lines=2, broken_at=1)


def test_no_network_on_the_offline_path(monkeypatch):
    """Any attempt to open a socket fails this test. The offline path must answer without one."""
    import socket

    def refuse(*a, **k):
        raise AssertionError("network access attempted")
    monkeypatch.setattr(socket, "socket", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    monkeypatch.delenv("TRUSTPACK_LIVE", raising=False)
    t = pipeline.ask("priya", "What is the net IRR of Halvane Growth Fund III?", write_audit=False)
    assert t["decision"] == "answered" and t["tokens"] == {"input": 0, "output": 0}


@pytest.mark.parametrize("text", ["UK passport 123456789.", "Passport AB1234567.", "Emirates ID 784196100000017.",
                                  "IBAN AE07 0000 0000 0000 0000 017.", "Born 14 May 1961.", "Call 050 000 0017.",
                                  "karim@gmail.com"])
def test_known_pii_gaps_are_still_gaps(text):
    """RED_TEAM.md lists these as formats the regex finder misses. If one starts passing, update the doc."""
    assert ingest.redact(text)[0] == text


def test_answer_text_is_the_verified_quote():
    """A live model could write any claim next to a real quote. The answer prints the quote, so it can't."""
    s = pipeline.state()
    hits = s["index"].search("Halvane commitment", ["investments"])
    fake = [dict(text="The fund is a strong buy.", chunk_id=hits[0][1].chunk_id, quote=hits[0][1].text[:20])]
    claims = pipeline.verify(fake, {c.chunk_id: c for _, c in hits})
    assert claims[0]["verified"]
    out = " ".join(f'{c["quote"]} [{c["chunk_id"]}]' for c in claims)
    assert "strong buy" not in out
