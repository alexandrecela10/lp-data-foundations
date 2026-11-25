# Trust Pack, M0: audit and plan

**Decision asked of the PM:** approve a new repo for the Trust Pack, the stack below, and the M1 to M4 plan. Nothing is built yet. Audited 2026-11-25.

**Correction to the brief:** `lp-data-foundations` is not a data-room Q&A prototype. It is the Portfolio Answer Desk: 60 questions over synthetic LP data, five data setups compared. It has no document chunker and no vector store.

## 1. What exists

| Item | lp-data-foundations (Answer Desk) | Lender Watch (read only) |
|---|---|---|
| Data | Synthetic world, bronze, silver, gold in DuckDB (`pipeline.py`) | Public SEC BDC data sets: 131,465 loan rows, each with a filing URL (`data/public/holdings.parquet`); 785 MB raw locally |
| Retriever | BM25 keyword search with a role filter applied before scoring (`foundations/search.py`) | Name search: TF-IDF, rapidfuzz, model2vec embeddings (`erm/retrieve.py`) |
| Vector store | None | None (in-memory pickle) |
| Chunker | None (whole documents) | None (one row per loan) |
| Embeddings | None | model2vec `potion-base-8M`, local, chosen because onnxruntime has no build for this Intel Mac |
| Model | `claude-sonnet-5-5`, only with a key and `ANSWERDESK_LIVE=1` (`llm.py`) | Claude judge, off by default because it sends names out |
| Contracts | Pydantic rows, failures to `silver.rejects` with a reason (`contracts.py`) | Exclusion reason per row (`connectors/bdc.py`) |
| Access | Per-role database copy; documents carry allowed roles (`access.py`) | None |
| Audit, tracing | JSONL audit (`governance.py`); Langfuse, no-op without keys (`tracing.py`) | Allowlisted JSON logs with request ID, no names (`telemetry.py`); Langfuse on judge calls |
| Eval | 60 questions with known answers; eval gate as pytest (`tests/test_eval_gate.py`) | Answer key, thresholds YAML, `make evals` fails below them |
| Docker, make, CI | None | `Dockerfile`, `compose.yaml`, `Makefile`, GitHub Actions CI with eval gate, approval-gated deploy and rollback scripts |
| Tests | 8 files, offline | 12 files, offline |

**Docker on this Mac:** works. Engine 25.0.2, Compose v2.24.3, 16 CPUs, 8 GB given to Docker, Intel x86_64.

## 2. What we reuse

| From | File | Use in the Trust Pack |
|---|---|---|
| Answer Desk | `foundations/search.py` | BM25 half of hybrid retrieval (M3 stretch) |
| Answer Desk | `contracts.py`, `governance.py` | Pattern for doc contracts, reject log, JSONL audit |
| Answer Desk | `access.py` `can_see_doc` | Pattern: filter before scoring, never after |
| Answer Desk | `llm.py` | Structured Claude call with strict JSON schema; live only behind a flag |
| Answer Desk | `tests/test_eval_gate.py` | Eval gate as tests |
| Lender Watch | `connectors/bdc.py`, `holdings.parquet` | Choose filings and derive numeric ground truth for the golden set |
| Lender Watch | `retrieve.py` (model2vec setup) | Local embeddings: no outbound call, works on Intel |
| Lender Watch | `telemetry.py` | Allowlisted log keys, request ID |
| Lender Watch | `Makefile`, `compose.yaml`, `ci.yml`, `evals/thresholds.yaml`, `scripts/rollback.sh` | Templates for `make`, Compose, CI gate, rollback |
| Lender Watch | `textparse.core` | Canonical company key for entity enrichment |

## 3. Gaps against the 12 layers

| # | Layer | Exists? | Gap | Plan |
|---|---|---|---|---|
| 1 | Ingestion, contracts | Partly (row contracts) | No document contract, no SHA-256, no date sanity | M1: `DocRecord` Pydantic model, reject log |
| 2 | Classification, PII | No | No labels | M1: label in the manifest; Presidio is stretch |
| 3 | Lineage | Partly (row to doc) | No chunk, offsets or versions | M1: chunk record with hash, page, offsets, 3 versions |
| 4 | Sovereignty | No | No boundary config | M1: `sovereignty.yaml`, `DATA_BOUNDARY.md` |
| 5 | Access control | Yes, by role | No deal rooms, not in a vector query | M1: room filter inside the pgvector SQL `WHERE` |
| 6 | Retrieval | BM25 and name search | No chunk-level vector search | M1: pgvector; hybrid with BM25 if time |
| 7 | Guardrails | Number check, advice refusal | No cite-or-abstain, no span check, no injection test | M3 |
| 8 | Offline eval | Yes, other tasks | No RAG metrics | M2: golden set, harness |
| 9 | Release gate | Lender Watch CI only | No prompt/index registry | M5 stretch; registry YAML lands in M2 |
| 10 | Tracing | No-op Langfuse | Not self-hosted, not per request | M4 |
| 11 | Audit, replay | JSONL audit | No replay | M4: `make replay ID=...` |
| 12 | Runbook | No | | M4: `RUNBOOK.md` |

## 4. Repo decision

- **Option A, inside lp-data-foundations.** Reuses code directly. But its `CLAUDE.md` makes all data synthetic, and its published case study numbers must stay stable.
- **Option B, new repo `trust-pack`.** Clean clone runs `make demo` alone. Reused files are copied with the source commit noted, not installed from the other repos.

**Recommendation: B.** Public SEC data breaks A's synthetic-only rule, and a CTO reads one focused repo faster than a fourth folder in a finished one.

## 5. M1 to M4 plan and first design choices

**M1 (contracts, lineage, ACL; about 4 h).** Ingest 6 to 9 filings, 3 deal rooms, 3 users. Done when bad docs are rejected with a logged reason, every chunk has full lineage, and user A gets 0 chunks from room B.
**M2 (golden set, harness; about 3 h).** 40 questions, `make eval` prints all metrics, saves a versioned run.
**M3 (guardrails; about 3 h).** Cite-or-abstain, span check, advice refusal, injection doc; all scored in the eval.
**M4 (trace, audit, docs; about 4 h).** One request in self-hosted Langfuse, `make replay`, TRUST.md, DEMO.md, RUNBOOK.md, DATA_BOUNDARY.md.

| Choice | Option 1 | Option 2 | Recommendation |
|---|---|---|---|
| Documents | Fetch filing HTML from EDGAR once, extract the schedule of investments to text, commit text plus a manifest (URL, original SHA-256) | Fetch at every `make demo` | 1: clean clone runs offline; the only runtime outbound flow stays the model API |
| Numeric ground truth | Read from Lender Watch's tagged XBRL rows | Hand-label from the text | 1: exact, and each number traces to a filing URL |
| Embeddings | model2vec `potion-base-8M`, local | Hosted embedding API | 1: no second outbound flow; runs on Intel |
| ACL enforcement | `WHERE deal_room = ANY(:allowed)` in the same SQL as the vector search | Postgres row-level security keyed on a session user | 1 first, RLS as a stretch: one line to show, one test to prove |
| Langfuse | Self-hosted v3 (web, worker, Postgres, ClickHouse, Redis, MinIO) | Self-hosted v2, one container | v3: v2 is no longer maintained and our SDKs are v3+. Risk: about 4 to 6 GB of the 8 GB Docker has |
| Registry | One `registry.yaml` with prompt, model, chunker, index versions | MLflow | YAML: fewer containers, readable in a diff |
| Judge | Claude, calibrated on 15 PM labels; offline stand-in without a key | Ragas metrics only | Own judge; Ragas as a cross-check only |
| Model terms | State Anthropic API defaults (no training on API data) and mark zero retention as "needs an agreement" | Claim zero retention | 1: claim only what is true; verify the retention text in M1 |

**Time risk:** about 14 h of build for 1.5 days. If short, cut hybrid retrieval and Presidio first, never the ACL test or the eval.

## 6. Name risks

- **Employer, clients, prospects:** none found. The PM's employer domain has 0 hits in either repo. Answer Desk passed its own name audit on 2026-10-25.
- **Lender Watch, public data (fine as data):** BDC filers and borrowers in SEC data, such as Blackstone, Goldman, KnowBe4 (`docs/decisions.md`, `outputs/analyses/matching-comparison.md`, `data/eval/*.csv`).
- **Lender Watch, to confirm by the PM:** 6 PE sponsors taken from their own websites (Thoma Bravo, Vista, Genstar, Alpine, Gryphon, Shore) in `data/sponsors/`, `app/review.py:120` and the opportunity analysis. Public, but if any is a client or prospect, it must not reach the Trust Pack. Plan: the Trust Pack uses no sponsor list.
- **New risk to avoid:** naming a sovereign cloud or bank provider in TRUST.md. Plan: say "an in-region managed endpoint", no provider name.

Synthetic labels and deal rooms, public filings. Not investment advice.
