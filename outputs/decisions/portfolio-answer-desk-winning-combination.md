---
decision_id: "PAD-06"
date: "2026-10-25"
product_area: "Product"
feature: "Portfolio Answer Desk"
prd_stage: "Solution Review"
decided_by: "Claude (unattended run); PM to ratify"
status: "active, offline and live evidence (2026-10-25)"
---

# Decision: One shared foundation, three front ends: chat for events, a governed dashboard for the pack, a briefing note for manager decisions

## What was decided

Build the answer desk on C+ids (warehouse tables, the semantic layer, an identity table, letter search with citations), and add the graph only for links between people and managers. Pair each request with its front end: chat (request 1), dashboard with 3 views (request 2), briefing note (request 3), SQL notebook for the data team.

## Why

**Offline** (`evals/results/offline-seed42.json`): fixed rules stand in for the AI. **Live** (`evals/results/live-claude-sonnet-5-5.json`): `claude-sonnet-5-5` reads every question for every setup, reads the passages in A and writes the SQL in B. 2 passes over the 60 questions, 960 calls, 0 failed calls, \$6.25 billed, 47 minutes. C+ids was rerun alone after it gained letter search (below): 120 calls, \$0.83.

| Setup | Request 1 (of 20) offline / live | Request 2 (of 20) | Request 3 (of 20) | Correct of 60 | Wrong numbers shown as sourced |
|---|---|---|---|---|---|
| A documents + search | 4 / 2 | 4 / 2 | 10 / 3 | 18 / 7 | 27 / 7 |
| B AI-written SQL | 3 / 2 | 6 / 3 | 13 / 6 | 22 / 11 | 0 / 0 |
| C semantic layer | 5 / 5 | 20 / 20 | 16 / 16 | 41 / 41 | 15 / 15 |
| C+ids (+ letter search) | 20 / 20 | 20 / 20 | 18 / 18 | 58 / 58 | 0 / 0 |
| D (C+ids + graph) | 20 / 20 | 20 / 20 | 20 / 20 | 60 / 60 | 0 / 0 |

- **Pre-registered rule** (PRD, written before any result): keep the graph for request 1 only if D beats C+ids by 2 or more questions or 2 or more minutes. **Result, offline and live: a tie, 20 against 20.** Median time on request 1: 53 s each offline, 51.8 s against 51.7 s live. So the graph doesn't earn its place for routes at this size.
- **Live, C, C+ids and D scored exactly as offline,** and gave the same answer on the rerun for all 60 questions. In these three setups Claude only fills in the question's fields; code computes the number.
- **Live, A lost 11 correct answers and B lost 11.** A gave the same answer on the rerun for 90% of questions, B for 80%; on reworded questions both agreed 50% of the time.
- **What broke C was spelling, not hops.** C found 2 of Calder's 5 routes: the other 3 sit under "Calder Pack." and "Calderwick Holdings". Recursive SQL walked the fund of funds hop without trouble. Adding an identity table fixed all 15 failures on request 1. Identity quality: the identity table matched 171 of 171 reported names correctly; exact names alone got 146 right, 3 wrong, 22 missed.
- **Where D wins:** the 2 questions about where Brennick's former partners went. B, with SQL on the people table, also answered both, offline and live; C and C+ids have no calculation defined for people.
- **C+ids changed after the first live run (2026-10-25).** It had no letter search, so D differed from it by two things, and C+ids missed a fee-offset letter the fixed-pattern reader can't parse: 2 wrong numbers shown with a source. With letter search added, C+ids differs from D only by the graph, scores 58 of 60 and shows 0 wrong numbers with a source, offline and live.
- **Request 2 needs no graph.** C, C+ids and D all score 20/20; the gain came from one versioned definition per metric.
- **Held-out world** (seed 7, spellings never tuned on): D 60/60, C+ids 58/60. The identity table left 11 of 184 names waiting for a person; no question touched them, which is a gap in the test set, not a result.

## What was NOT chosen

| Alternative | Why rejected |
|---|---|
| Documents + chatbot only (A) | 18/60 offline, 7/60 live; 27 and 7 wrong numbers shown with real citations |
| AI-written SQL only (B) | 22/60 offline, 11/60 live; definitions and point in time don't live in the schema |
| Graph as the main engine (D everywhere) | No gain on routes or numbers at this size; adds a second copy of the data to keep in step |
| One front end for all three requests | The pack needs a fixed as-of date and export; the CIO needs a paragraph; the head of PE needs quotes |

## Consequences

**Enables:** the same number in chat, dashboard and notebook; refusals that name who can answer.
**Prevents:** free-form questions outside the metric menu.

## Open questions remaining

- [x] Live run with `claude-sonnet-5-5`, same model and budget for all five setups (2026-10-25). Same ranking as offline.
- [x] C+ids showed 2 wrong numbers with a source (guardrail is zero). PM chose to fix C+ids (2026-10-25): letter search added; 0 offline and live.
- [ ] Timed human run (design in the PRD). @PM

## Review trigger

Revisit if the live run moves any setup by 3 or more questions, or if a real portfolio shows routes deeper than 3 holdings.

**Trigger fired on 2026-10-25:** live moved A and B by 11 questions each. Reviewed: the moves were in the two setups not recommended; C, C+ids and D did not move, so the decision stands.
