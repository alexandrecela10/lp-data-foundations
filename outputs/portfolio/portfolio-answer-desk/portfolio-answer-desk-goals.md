# Portfolio Answer Desk case study: goals

From `.claude/pm-os/portfolio/portfolio-goals.md`, applied to this project.

| # | Criterion | How to check | Status (2026-10-25) |
|---|---|---|---|
| 1 | The top of the page states the problem, the player and the personas, and links a demo | Read the first screen | Partial: demo not deployed yet; button reads "deploy pending" |
| 2 | Every tackled problem has one row with job, hypothesis, metric and result | Count rows in section 04 | Pass (3 of 3) |
| 3 | Untackled or partial problems appear under non-goals or sub-problems | Compare lists | Pass |
| 4 | No client, employer or prospect name; no real organisation next to a synthetic fact | `name-audit.md` | Pass, PM to confirm "Calder Packaging" |
| 5 | Every number traces to `evals/results/*.json` or is marked assumed or unobserved | The page is built from the result files | Pass: offline and live labelled; time saved marked assumed |
| 6 | Zero em dashes, zero banned words | grep | Pass |
| 7 | LinkedIn description 2,000 characters or fewer | `wc -m` | Pass (1,706) |
| 8 | Every link returns 200 | curl | Pass for external links; repo private until published |

**Passing bar:** all 8 pass before publishing. Blocked on the PM: deploy the demo, make the repo public or link a public mirror.
