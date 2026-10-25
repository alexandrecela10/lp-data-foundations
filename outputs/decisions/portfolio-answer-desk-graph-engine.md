---
decision_id: "PAD-01"
date: "2026-10-25"
product_area: "Data foundation"
feature: "Portfolio Answer Desk"
prd_stage: "Solution Review"
decided_by: "Claude (unattended run); PM to ratify"
status: "active"
---

# Decision: Walk ownership routes with recursive SQL in the semantic layer; use a NetworkX graph only for people links and for teaching; keep DuckPGQ as a measured option

## What was decided

Look-through exposure walks routes with a recursive SQL query (depth limit 5, cycle guard) inside the governed metric. A NetworkX graph, built from gold for the as-of date, answers questions about people and managers (where a departed partner went), cross-checks the route total, and draws the picture in the demo. DuckPGQ is timed in the scale runs but not used to answer.

## Why: the measured trade-off

**Correctness at the demo size** (`evals/results/offline-seed42.json`): recursive SQL and the graph return the same Calder Packaging total (\$8.06m, 5 routes) and the same answers on all 20 event questions. The graph adds 4 correct answers, all on people links or letters, none on routes.

**Time** (`evals/results/scale.json`, median of repeated runs, one laptop):

| Size | Funds | Documents | Full rebuild | Routes: recursive SQL | Routes: build graph + walk | Routes: DuckPGQ query | Pooled TVPI (governed metric) | Peak memory |
|---|---|---|---|---|---|---|---|---|
| 1x | 25 | 2,300 | 1.0 s | 37 ms | 20 + 2 ms | 13 ms | 27 ms | 208 MB |
| 10x | 563 | 33,835 | 4.2 s | 80 ms | 59 + 29 ms | 16 ms | 508 ms | 399 MB |
| 100x | 5,902 | 333,578 | 99 s | 538 ms | 438 + 297 ms | 25 ms | 9,253 ms | 1,531 MB |

- **Routes stay under a second every way, up to 100x.** The graph walk beats recursive SQL only once the graph is already built (297 ms against 538 ms at 100x); building it costs 438 ms and a second copy of the data.
- **DuckPGQ is the fastest query** (25 ms at 100x) but its timing excludes setting up its own node and edge tables, it is a research project, it needs DuckDB 1.4.4 (its syntax fails on 2.0.0 in our test), and listing every route needs one fixed-length pattern per route length.
- **What breaks first at 100x is not routes.** A governed metric computed one fund at a time takes 9.3 s, and matching company names takes 68 s of the 99 s rebuild. Both are our code's patterns (one query per fund; pairwise name comparison), fixable without a graph.
- **Optional E (graph only for sums):** one walk summed packaging exposure in 319 ms against 685 ms in SQL at 100x, same total. Graphs were not poor at sums here; the cost is keeping the graph in step with gold.

## What was NOT chosen

| Alternative | Status and licence (checked 2026-10-25) | Why rejected |
|---|---|---|
| DuckPGQ for answers | MIT, research project, active ([repo](https://github.com/cwida/duckpgq-extension)); DuckDB docs recommend 1.4.4 | Fixed-length patterns to list every route; version pin; extension download at start on Streamlit Cloud |
| Kùzu (embedded graph database) | MIT, repository archived October 2025 ([The Register](https://www.theregister.com/2025/10/14/kuzudb_abandoned/)); forks exist | No security fixes from the original project; not worth a new dependency |
| Neo4j Community | GPLv3, server | Needs a server; the demo must run with none |
| Graph everywhere (D for numbers too) | | Same answers, a second copy of the data, no gain on routes at this size |

## Consequences

**Enables:** one copy of the data for numbers; the graph picture and people links where they help.
**Prevents:** analysts writing graph queries themselves (they pick governed metrics instead).

## Review trigger

Revisit if real portfolios show routes deeper than 3 holdings, if route questions must answer in under 100 ms at 100x, or if people-and-deal link questions grow past a handful.
