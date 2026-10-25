# Architecture

**What it is.** A portfolio question desk for the private equity team of a large LP, plus a test bench that runs 60 questions through five data setups. Python 3.11, DuckDB 1.4.4 in memory, Pydantic, NetworkX, Streamlit. No server. Synthetic data. Not investment advice.

```
world.py (seed) -> sources.py (6 sources, each with its own dates)
   -> pipeline.py: bronze (as received) -> silver (contracts, identity matching) -> gold (typed, lineage)
   -> access.py: a per-role copy of gold (restricted columns and rows absent)
   -> semantic/ (metric registry + compiler + pure functions)   graph.py (routes, identity, people)
   -> foundations/ A, B, C, C+ids, D   (nlu.py reads the question; llm.py when live)
   -> answer.py (number check, disclaimer, checking-time model)
   -> interfaces.py (chat, dashboard, notebook, briefing)   evals.py (60 questions)   scale.py (10x, 100x)
```

## Sources

| Source | Rhythm | Shape | Read into |
|---|---|---|---|
| Holdings (accounting system) | daily snapshot | rows | `silver.positions`, `silver.planned` (restricted) |
| Notices (calls, distributions) | when sent, about weekly | email + PDF text | `silver.cashflows`; malformed ones to `silver.rejects` |
| Reports (fund quarterly, co-investment statements) | quarterly, 40 to 90 days late | text, 4 layouts | `silver.reports`, `report_holdings`, `fof_stakes`, `coinvest_statements` |
| Letters | whenever | free text | `silver.letters`; fixed-pattern events into `silver.events` with confidence |
| Reference | slow-changing | rows | companies (parents), managers, funds, people |
| News | every 15 minutes | free text | `silver.news` (text only: never a source of numbers) |

## The five setups

| Setup | What reads the question | Where numbers come from | Identity | Routes |
|---|---|---|---|---|
| A documents + search | AI (offline: shared reader) | passages the AI reads | first name and holding-company sheet | whatever the passages show |
| B tables + AI SQL | AI | SQL the AI writes on curated views | exact name and parent links | one level of fund of funds |
| C semantic layer | AI picks a metric | governed metric | exact name only | recursive SQL, any depth |
| C+ids | AI picks a metric | governed metric | identity table | recursive SQL |
| D | AI picks and routes | governed metric | identity table and graph | graph walk, cross-checked with SQL |

Offline, a fixed reader (`nlu.py`) reads every question for every setup, so understanding the question never separates them. A's and B's offline readers are stand-ins written from the documented mechanism; see the module docstrings for exactly what they do and don't do.

## Governance

- **Roles:** `access.ROLES`. Sara (analyst) can't see co-investment fee terms (columns) or unapproved planned commitments (rows). Every setup queries a per-role copy; search drops documents the role can't see.
- **Metric registry:** `semantic/metrics.yaml`, owner, versions with dates, a plain sentence, tests in `tests/test_metrics.py`.
- **Point in time:** two dates on every fact; "as of D" counts what happened and was learnt by D.
- **Lineage:** every gold row keeps its `doc_id`; `governance.lineage(store, doc_id)` returns the bronze document.
- **Contracts:** `contracts.py`; failures logged in `silver.rejects`.
- **Audit log:** `governance.audit` for every chat answer (session in the hosted demo, `logs/audit.jsonl` locally).
- **Refusals:** no governed definition, role can't see it, a news figure, or advice.

## Commands

```
pip install -e ".[app,dev]"            # or: uv pip install -e ".[app,dev]"
PYTHONPATH=src python -m answerdesk.cli all     # rebuild, evaluate, scale; writes evals/results/
pytest                                           # 60+ tests, no key needed
streamlit run app.py
ANTHROPIC_API_KEY=... PYTHONPATH=src python -m answerdesk.cli live    # live evaluation, costs money
```

## Licences of what we use or compared (checked 2026-10-25)

| Component | Licence | Status | Used |
|---|---|---|---|
| DuckDB | MIT | active | yes, 1.4.4 |
| DuckPGQ | MIT ([repo](https://github.com/cwida/duckpgq-extension)) | research project, active (last push 23 Oct 2026); syntax fails on DuckDB 2.0.0 in our test | timed in scale runs only |
| NetworkX | BSD-3-Clause | active | yes |
| Pydantic, PyYAML, pandas, Streamlit, Altair | MIT / BSD / Apache 2.0 | active | yes |
| MetricFlow | Apache 2.0 from 0.209 | active | no (see decision PAD-02) |
| Boring Semantic Layer | MIT | active | no |
| Cube Core | Apache 2.0 | active, server | no |
| Kùzu | MIT | archived October 2025 ([The Register](https://www.theregister.com/2025/10/14/kuzudb_abandoned/)); forks exist | no |
| Neo4j Community | GPLv3 | active, server | no (needs a server) |
| Anthropic SDK | MIT | active | live mode only |
