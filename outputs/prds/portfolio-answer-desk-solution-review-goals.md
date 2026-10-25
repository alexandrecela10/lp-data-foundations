# Portfolio Answer Desk PRD (Solution Review): goals

| # | Exit criterion | How to check |
|---|---|---|
| 1 | Each problem row has one hypothesis and one metric with a target | Read the Hypothesis table |
| 2 | The AI Behavior Contract has a happy path, an edge case and three "should refuse" rows (role, no definition, news number) | Read the table |
| 3 | Every blocker in the review synthesis has a fix in the PRD | Compare the synthesis table with the PRD |
| 4 | Thresholds for "the graph earns its place" are written before any eval result exists | Commit order: PRD commit precedes `evals/results/` |
| 5 | No "today" value is stated as observed without a source | Read every "Today" cell |
| 6 | The disclaimer rule, per-role access and the hosted-demo scope are in the contract | Read the contract |
| 7 | Zero em dashes, zero banned words | grep |

**Passing bar:** all 7 pass. Word count runs above the 1,500 guide for this stage because the review fixes added detail; the appendix holds it.
