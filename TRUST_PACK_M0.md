# Trust Pack, M0: audit and plan (v2)

**Decision asked of the PM:** approve the v2 plan. The Trust Pack becomes one interactive page plus a small offline pipeline behind it, set in a UAE family office. No Docker, no Postgres, no self-hosted Langfuse. Nothing is built yet. Audited 2026-11-25, revised the same day.

**What changed in v2 (PM direction, 2026-11-25):** deliverables are visual and interactive; the setting is a single family office in the UAE; lightweight, not production grade.

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

**Docker on this Mac:** works (Engine 25.0.2, Compose v2.24.3, 8 GB for Docker). v2 doesn't need it.

## 2. What we reuse

| From | File | Use in the Trust Pack |
|---|---|---|
| Answer Desk | `foundations/search.py` | BM25 retrieval, with the access filter before scoring |
| Answer Desk | `contracts.py`, `governance.py` | Doc contracts, reject log, JSONL audit |
| Answer Desk | `llm.py` | Optional live Claude call; offline path by default |
| Answer Desk | `explainer.py`, `static/foundations.html` | Pattern: build a static interactive page from run results |
| Answer Desk | `tests/test_eval_gate.py` | Eval gate as tests |
| Lender Watch | `telemetry.py` | Allowlisted log fields, request ID |
| Lender Watch | `evals/thresholds.yaml`, `scripts/rollback.sh` | Shown on the page as the release-gate and rollback pattern, not rebuilt |

## 3. Gaps against the 12 layers (v2: each layer is a step on the page)

| # | Layer | Exists? | Gap | Plan |
|---|---|---|---|---|
| 1 | Ingestion, contracts | Partly | No document contract, no SHA-256 | M1: `DocRecord` model, reject log, 2 planted bad docs |
| 2 | Classification, PII | No | No labels, no PII handling | M1: label per doc; regex PII finder with a redaction log (passport, Emirates ID, IBAN formats, all fake) |
| 3 | Lineage | Partly | No chunk, offsets or versions | M1: chunk record with hash, offsets, 3 versions |
| 4 | Sovereignty | No | No boundary config | M1: `sovereignty.yaml`; the page draws every data flow |
| 5 | Access control | Yes, by role | No family roles or rooms | M1: room filter before retrieval scoring |
| 6 | Retrieval | BM25 | | Reuse BM25 |
| 7 | Guardrails | Advice refusal | No cite-or-abstain, span check, injection test | M2 |
| 8 | Offline eval | Other tasks | No RAG metrics | M2 |
| 9 | Release gate | Lender Watch only | | Shown on the page, thresholds as tests; CI is stretch |
| 10 | Tracing | No-op Langfuse | | M3: trace JSON in Langfuse's shape, drawn on the page |
| 11 | Audit, replay | JSONL audit | No replay | M3: `make replay ID=...` |
| 12 | Runbook | No | | M3: drawn as a flow on the page |

## 4. Repo decision

- **Option A, a `trust_pack/` folder in this repo.** The data is now synthetic, so it fits this repo's rules. No new repo to set up.
- **Option B, a new `trust-pack` repo.** Cleaner story, more setup.

**Recommendation: A.** v2's synthetic data removes the reason for B, and a folder is faster for a Friday deadline. It can move to its own repo later in an hour.

## 5. The UAE family office setting

**The family office (invented):** one family, a principal, two next-generation members, a CIO, and an external lawyer. Three rooms: Family governance (foundation charter, succession memo, KYC files with fake PII), Investments (fund reports, capital calls, co-investment memos), Advisor share (two deals shared with the lawyer).

| User | Sees | Example question that must fail |
|---|---|---|
| Principal | All rooms | none |
| Next-gen member | Investments | "Who are the foundation's beneficiaries?" (0 governance chunks) |
| CIO | Investments, Advisor share | "Show me the principal's passport number" (redacted) |
| External lawyer | Advisor share | "What did we commit to Fund X?" (0 investment chunks) |

**What the page teaches (the SME part), each claim checked against the official text in M4 and linked:**
- **Which data law applies depends on where the office is set up:** onshore UAE (Federal Decree-Law 45 of 2021, the PDPL), DIFC (Data Protection Law No. 5 of 2020, with its regulation on AI and autonomous systems), or ADGM (Data Protection Regulations 2021).
- **Where data and the model run:** in-country storage, an in-region model endpoint, and what "no training, limited retention" means in a contract.
- **What a family office protects that a fund doesn't:** family members' identity documents, succession plans, who gets what. A leak is personal, not only financial.
- **The classic ML to LLM mapping table,** from the original spec, as hover cards.

## 6. M1 to M3 plan (about 10 h) and first design choices

**M1 (about 3 h): data room, contracts, labels, lineage, access.** Done when 2 bad docs are rejected with a reason, every chunk has lineage, and the lawyer gets 0 chunks from other rooms.
**M2 (about 3 h): golden set, harness, guardrails.** 30 questions, `make eval` prints recall@5, citation accuracy, abstention accuracy, access violations, injection and advice results, saved with versions.
**M3 (about 4 h): the interactive page.** Built from the run's JSON. Tabs: one question end to end (switch user, watch chunks get filtered, see the cited answer, the scores and the trace); the scoreboard; the mapping table; the UAE data-flow map; the runbook. Also `make replay`, a short `TRUST.md`, a name audit.
**Stretch:** live Claude answers and an LLM judge, CI gate.

| Choice | Option 1 | Option 2 | Recommendation |
|---|---|---|---|
| Data | Invented family office documents, about 25, with fake PII | Public SEC filings (v1) | 1: a family office's risk is personal data, which SEC filings can't show |
| Format | One static HTML page, published as a private Artifact and committed | Streamlit app | 1: opens on a phone, nothing to run, easy to share after the interview |
| Answers | Offline extractive answerer: picks the cited sentence, abstains under a score floor | Claude on every answer | 1 by default, Claude behind a flag: the demo needs no key, and numbers stay reproducible |
| Tracing | Trace JSON per request in Langfuse's shape | Self-hosted Langfuse | 1: same fields, no 6 containers; the page says where Langfuse would sit |
| Retrieval | Reuse BM25 | Add embeddings | 1: 25 docs don't need vectors; the page names when they would |

## 7. Name risks

- **Employer, clients, prospects:** none found. The PM's employer domain has 0 hits in either repo.
- **Lender Watch public data:** BDC filers and borrowers (Blackstone, Goldman, KnowBe4) and 6 PE sponsors from their websites. v2 uses none of it.
- **New risks in v2:** an invented family name that matches a real UAE family, and naming a cloud provider. Plan: search every invented name before use; say "an in-region model endpoint", no provider.

Synthetic data. Not investment advice.
