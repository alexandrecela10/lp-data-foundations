---
decision_id: "PAD-02"
date: "2026-10-25"
product_area: "Data foundation"
feature: "Portfolio Answer Desk"
prd_stage: "Solution Review"
decided_by: "Claude (unattended run, PM approved the workflow); PM to ratify"
status: "active"
supersedes: ""
---

# Decision: Use a small YAML metric registry of our own as the semantic layer

## What was decided

Define every governed metric once in `src/answerdesk/semantic/metrics.yaml` (owner, versions with dates, a plain sentence, dimensions) and compile requests to SQL in `semantic/layer.py`, with the maths in pure functions (`semantic/fin.py`).

## Why

- **Point in time is the hard part, and it fits.** Every metric filters on two dates (when it happened, when we learnt it). Example: as of 9 September the Calder write-down doesn't count; as of 10 September it does. Look-through exposure also needs a recursive walk and event adjustments. In our own layer that is one SQL template.
- **Measured dependency cost** (`uv pip install --dry-run`, 2026-10-25): our layer adds 1 package (PyYAML). Boring Semantic Layer adds 14 (it brings Ibis). MetricFlow with dbt-duckdb adds 59 and needs a dbt project.
- **Measured result:** C, C+ids and D answer all 20 committee-pack questions correctly offline, including the "last quarter's definition" trap (unfunded v1 against v2), and return the same answer on rerun and on 3 rephrasings (`evals/results/offline-seed42.json`). Live, with `claude-sonnet-5-5` reading each question, the same three setups again answered 20 of 20 and gave the same answer on the rerun for every question (`evals/results/live-claude-sonnet-5-5.json`). B, where Claude writes the SQL itself, answered 3 of 20 pack questions live.

## What was NOT chosen

| Alternative | Status and licence (checked 2026-10-25) | Why rejected |
|---|---|---|
| MetricFlow (dbt Labs) | Apache 2.0 from v0.209 ([announcement, Oct 2025](https://www.getdbt.com/blog/open-source-metricflow-governed-metrics)); repo active, last push 13 Oct 2026; [MetricFlow repo](https://github.com/dbt-labs/metricflow) | 59 packages and a dbt project for 15 metrics; expressing "learnt by D" and a recursive look-through needs custom models anyway. Assessed from docs and the dependency count, not built |
| Boring Semantic Layer | MIT ([repo](https://github.com/boringdata/boring-semantic-layer)); active, last push 24 Aug 2026 | 14 packages; good fit for simple aggregates, but the recursive route walk and as-of logic would sit outside it. Assessed, not built |
| Cube Core | Apache 2.0 core ([repo](https://github.com/cube-js/cube)) | Runs as a server; the demo must run on Streamlit Community Cloud with no servers |

## Consequences

**This decision enables:** one definition per metric with an owner and a version; refusals when no definition exists (PME, gross IRR); a "changed since last pack" banner; the same number in chat, dashboard and notebook.

**This decision prevents:** other BI tools reading our definitions in a standard format. Migration path: the YAML keeps MetricFlow-like fields (measures, dimensions, versions), so moving to MetricFlow or an Open Semantic Interchange format later is a translation, not a redesign.

## Open questions remaining

- [ ] Which team owns look-through exposure in a real LP: risk or investment? @PM

## Review trigger

If the registry passes 50 metrics or a second tool must read the definitions, revisit MetricFlow.
