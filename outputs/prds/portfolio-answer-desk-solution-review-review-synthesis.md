---
prd: portfolio-answer-desk-solution-review.md
review_date: 2026-10-25
stage: Solution Review
agents: [engineer, designer, executive, legal, uxr, skeptic, customer]
---

# PRD Review Synthesis: Portfolio Answer Desk

**Reviewed:** 2026-10-25, seven reviewer sub-agents run in parallel, each reading the PRD and the brief.
**Current Stage:** Solution Review

## TL;DR

**Overall assessment:** needs fixes before build. All fixes are in the PRD now (see "Fixed in PRD").
**Critical blockers:** 12 (after merging duplicates). **Important gaps:** 9. **Conflicts:** 2.
**Next step:** build with the fixes; record the two PM decisions in the state file.

## Critical blockers and how each was fixed

| # | Blocker | Flagged by | Fix applied |
|---|---|---|---|
| 1 | The disclaimer "Synthetic data. Not investment advice." is missing from screens, copied text and exports | Legal | On every screen, in copied answers and exports; a test fails without it |
| 2 | Foundation B's SQL can read restricted columns (co-investment fees) | Legal, Engineer | Every foundation runs against per-role DuckDB views; A's search drops restricted documents; trap questions for B in the gate |
| 3 | Live AI calls in the public demo are unscoped | Legal | The hosted demo runs offline only. Live calls happen only locally with a key, with a notice that questions go to Anthropic |
| 4 | The as-of rule is undefined | Engineer | Every event carries two dates: when it took effect and when we learnt of it. As of a date means "learnt on or before that date" |
| 5 | Nothing checks the numbers in AI-written text | Engineer | Numbers enter the text through placeholders; a checker extracts every number from the final text and fails closed if one isn't in the computed set |
| 6 | Look-through can double count or loop | Engineer | Routes are kept per end holding, duplicate report rows are removed, the walk has a cycle guard and a depth limit of 5. Tests for each |
| 7 | 100x runs may not fit Streamlit Cloud; DuckPGQ downloads at start | Engineer | Scale runs locally, results committed, the demo reads them. DuckDB pinned to 1.4.4; recursive SQL is the fallback if DuckPGQ won't load |
| 8 | The eval gate guarantees C and D win; offline A and B are strawmen | Skeptic | Offline results are labelled a mechanism test. A gets query expansion from the company reference text; B gets curated views with column notes and parent links. The ranking is confirmed only by the live run, same model and budget for all arms |
| 9 | Known answers are circular (same author's definitions) | Skeptic | Definitions written first in `docs/DEFINITIONS.md`; truth code reads generator objects only; a held-out world (another seed, extra name noise never tuned on) is scored separately |
| 10 | The graph has no number to earn its place; the alias-table arm is missing | Skeptic, Executive | C plus an alias table ("C+ids") is a scored arm. Threshold set before the run: keep the graph only if D beats C+ids by 2 or more questions on request 1, or by 2 or more minutes median |
| 11 | The baseline "hours" was never measured; the timed run has no design | UXR | "Hours" dropped from every claim. Timed run designed: 3 to 5 former LP analysts, three arms (manual, A, winner), counterbalanced, different company per arm |
| 12 | Only the happy path is designed; education visuals have no place | Designer, Customer | Refusal card, "waiting for review" line, empty card and offline banner added. Graph walk sits behind "Show routes on the graph" with a "Next hop" button; the route table is the main view; hops are numbered, not colour only |

## Important gaps (addressed or recorded)

- **Business case rests on time saved.** Executive. Added a risk line: the value is fewer wrong numbers reaching the CIO and fewer pack corrections. Time saved alone does not justify the build.
- **Identity matching untested.** Executive. The generator adds unlinked variants and near-duplicates; the eval reports matches right, wrong and missed per foundation; setup effort per LP is marked assumed.
- **Checking time drives the result.** UXR, Skeptic. Sensitivity table: half and double the per-number times, plus "share of sourced numbers rechecked by hand" at 0%, 50% and 100%.
- **Stale numbers look current.** Customer, Designer. Each route shows its own as-of date; sources older than 90 days show "stale"; the first line says "as of mixed dates" when they differ.
- **Definition in plain words.** Customer. Each metric has one plain sentence (what's counted, currency), shown under the answer.
- **IRR edge cases, currency, follow-up memory.** Engineer. IRR solved by bisection; no sign change returns "not meaningful". All amounts in US dollars (stated). A follow-up reuses the last request's metric and filters.
- **Audit log on Streamlit Cloud is lost on restart.** Engineer. Stated: the hosted log lives for the session; local runs write a file.
- **Names may match real firms.** Legal. Checked by web search: "CPG Holdings" is close to a real building-products company, so the holding company is renamed "Calderwick Holdings". "Calder Packaging" has no exact match (a packaging-machinery firm uses a longer name); kept because the brief defines it, flagged in the name audit.
- **Notes on an answer.** Customer. Sara can add a note that travels with the copied answer.

## Conflicting perspectives

1. **Cut foundation E (Executive) against keep it optional (brief).** Decision: build E only as a timing comparison at scale, not as an answerer. PM to confirm.
2. **Rank only on the live run (Skeptic) against "what won" in the brief.** Decision: publish offline results as a mechanism test with that label, plus the live command. The PM must decide whether the case study waits for the live run (recommendation: yes for the headline, no for the demo).

## Detailed feedback by perspective (short)

- **Engineering:** good split (AI picks, code computes) and offline default. Complexity M. Blockers 4 to 7 above.
- **Design:** answer-first card and one CTA per screen work. Usability risk medium until refusal and empty states exist.
- **Executive:** strong governance story; weak money case; identity is the expensive part. Strategic fit moderate to strong.
- **Legal:** synthetic-only is right; disclaimer, per-role views, hosted-demo scope were missing. Licences fine with notices; Kuzu benchmark-only; MetricFlow 0.209 or later.
- **UX research:** honest labelling of assumptions; baseline and time model unvalidated. Research validation weak.
- **Skeptic:** offline bench can't lose for C and D; circular truth; strawmen. Fixed by labels, held-out world, stronger baselines, thresholds before the run.
- **Customer (Sara):** "I would use this" if hidden exclusions, stale dates and missing click-through are fixed. Would use it.

## Action items

- [x] Apply blockers 1 to 12 to the PRD and the build. Owner: Claude
- [ ] Timed human run, 3 to 5 analysts. Owner: PM
- [ ] Live eval with `claude-sonnet-5-5`, 3 reruns. Owner: PM (one command)
- [ ] Decide on conflicts 1 and 2. Owner: PM
