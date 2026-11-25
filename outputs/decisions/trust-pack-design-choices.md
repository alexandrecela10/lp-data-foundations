# Decision: Trust Pack design choices

Date: 2026-11-25. Area: Trust Pack (`trust_pack/`, `src/trustpack/`). Decided by: the PM approved the v2 plan; Claude made the build calls below.

**Decision.** Build the Trust Pack as an offline pipeline plus one interactive page, set in an invented UAE family office, inside this repo.

| Choice | Chosen | Not chosen, and why | Enables / prevents | Revisit when |
|---|---|---|---|---|
| Data | 23 invented documents with fake PII | Public SEC filings: no personal data, so they can't show the family office's main risk | Shows PII redaction and family-only rooms / no real-world numbers | A real data room is available |
| Access control | Room filter before scoring | Filter after generation: 16 forbidden passages would have reached the answer step on 4 test questions | 0 cross-room passages by construction | Per-document exceptions are needed |
| Answerer | Offline extractive, abstains under rules | Claude on every answer: needs a key, costs money, numbers not reproducible | Runs with no key; fails safe / 50% coverage on the holdout | Before any real user; run the live path under the same checks |
| Tracing | Trace JSON with Langfuse-style fields | Self-hosted Langfuse: 6 containers for a demo | Light / no trace UI | Production |
| Retrieval | BM25 (reused) | Embeddings: 46 passages don't need them | Simple, explainable / misses synonyms | Corpus over a few thousand passages, or reworded questions dominate |
| Eval honesty | Added a 10-question holdout after freezing the rules | Report test only: I had read test failures, so it overstates | A fair coverage number (0.5) | Every rule change |

Consequences: the gate passes on test; the holdout shows the coverage cost. Not done: LLM judge and calibration, CI workflow, live run.
