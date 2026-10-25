---
decision_id: "PAD-04"
date: "2026-10-25"
product_area: "Data foundation"
feature: "Portfolio Answer Desk"
prd_stage: "Solution Review"
decided_by: "Claude (unattended run); PM to ratify"
status: "active"
---

# Decision: Bronze, silver, gold in in-memory DuckDB 1.4.4, rebuilt in batch from each source's schedule

## What was decided

Every document lands in `bronze.documents` as received, with `learnt_at` and `as_of`. Silver reads it into fixed fields behind Pydantic contracts and matches company names. Gold holds typed tables with the `doc_id` behind every row. The whole build reruns from the seed in about 1.5 s at the demo size (`evals/results/offline-seed42.json`, `meta.pipeline_seconds`). DuckDB is pinned to 1.4.4.

## Why

- **Bad rows are blocked, not mixed in.** 26 malformed notices (European number format) are rejected in silver with the reason, and their corrected copies load (`tests/test_data.py::test_bad_rows_are_blocked_and_logged`). Counterfactual: in one flat table, "USD 1.933.184,00" would have parsed as 1.933 or failed silently.
- **Batch, not streaming.** Secondaries Radar measured both paths on the same data: identical results, rebuild from bronze 10.1 s batch against 12.6 s stream, and a decision window of weeks (`firstcall/LEARNING.md` in that repo). Sources here arrive daily to quarterly; nothing is decided within minutes.
- **DuckDB 1.4.4, not 2.0.** Tested 2026-10-25: the DuckPGQ extension installs on DuckDB 2.0.0 but its `CREATE PROPERTY GRAPH` syntax fails to parse; on 1.4.4 it works. The [DuckDB docs](https://duckdb.org/docs/current/guides/sql_features/graph_queries) recommend 1.4.4 for DuckPGQ.

## What was NOT chosen

| Alternative | Why rejected |
|---|---|
| One flat table per source | No place to block bad rows or keep two dates per fact |
| A server warehouse (Postgres, cloud) | The demo must run on Streamlit Community Cloud with no servers |
| Streaming ingest | Measured in Secondaries Radar: same answers, more moving parts, no decision needs seconds |

## Consequences

**Enables:** point in time on every fact; lineage from any number to its document; one command rebuilds everything.
**Prevents:** persistence across restarts on Streamlit Cloud (the audit log lasts for the session there).

## Review trigger

If a source starts arriving faster than daily and a decision depends on it within the hour, revisit streaming.
