# Portfolio case studies: goals

Scope: six projects, each with a case study page on the portfolio hub and a LinkedIn entry. Deck Rank is the reference; the others follow `/portfolio-case-study`.

## Exit criteria (each project)

| # | Criterion | How to check |
|---|---|---|
| 1 | The top of the page states the problem, the private capital player and the personas, and links a demo | Read the first screen |
| 2 | Every sub-problem is marked tackled or not; every tackled one has one hypothesis card with before → after, if/then/because, metric and test | Count sub-problems vs cards |
| 3 | Every untackled or partial sub-problem is listed under non-goals | Compare the two lists |
| 4 | No client, target or employer-prospect company name appears in the page, LinkedIn text, demo UI, repo code, test fixtures, seed data or PDF text | `/name-audit` re-run returns zero hits, or the PM has accepted the remaining ones |
| 5 | Every number is observed in a named artifact (code, log, test) or marked "unobserved" | Trace each number |
| 6 | Zero em dashes, zero banned words, and the minimal factual rule in CLAUDE.md is met | Grep + read |
| 7 | LinkedIn description is 2,000 characters or fewer | `wc -m` |
| 8 | Every link returns 200 | `curl -o /dev/null -w "%{http_code}"` |

## Passing bar

All 8 criteria pass before a project is marked ready. Alex approves each project before any repo edit, push or publish.
