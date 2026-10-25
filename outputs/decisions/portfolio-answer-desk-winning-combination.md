---
decision_id: "PAD-06"
date: "2026-10-25"
product_area: "Product"
feature: "Portfolio Answer Desk"
prd_stage: "Solution Review"
decided_by: "Claude (unattended run); PM to ratify after the live run"
status: "active, offline evidence only"
---

# Decision: One shared foundation, three front ends: chat for events, a governed dashboard for the pack, a briefing note for manager decisions

## What was decided

Build the answer desk on C+ids (warehouse tables, the semantic layer, an identity table), add the graph only for links between people and managers, and add letter search with citations for manager history. Pair each request with its front end: chat (request 1), dashboard with 3 views (request 2), briefing note (request 3), SQL notebook for the data team.

## Why (offline mechanism test, `evals/results/offline-seed42.json`)

| Setup | Request 1 (of 20) | Request 2 (of 20) | Request 3 (of 20) | Wrong numbers shown as sourced |
|---|---|---|---|---|
| A documents + search | 4 | 4 | 10 | 27 |
| B AI-written SQL | 3 | 6 | 13 | 0 |
| C semantic layer | 5 | 20 | 16 | 15 |
| C+ids | 20 | 20 | 16 | 2 |
| D (C+ids + graph + letter search) | 20 | 20 | 20 | 0 |

- **Pre-registered rule** (PRD, written before any result): keep the graph for request 1 only if D beats C+ids by 2 or more questions or 2 or more minutes. **Result: a tie, 20 against 20, same median time (53 s on request 1).** So the graph doesn't earn its place for routes at this size.
- **What broke C was spelling, not hops.** C found 2 of Calder's 5 routes: the other 3 sit under "Calder Pack." and "Calderwick Holdings". Recursive SQL walked the fund of funds hop without trouble. Adding an identity table fixed all 15 failures on request 1. Identity quality: the identity table matched 171 of 171 reported names correctly; exact names alone got 146 right, 3 wrong, 22 missed.
- **Where D wins:** 4 manager-history questions. 2 need people links (where a departed partner went: the graph), 2 need a letter about a fee offset, which the fixed-pattern letter reader can't parse and letter search finds.
- **Request 2 needs no graph.** C, C+ids and D all score 20/20; the gain came from one versioned definition per metric.
- **Held-out world** (seed 7, spellings never tuned on): D 60/60, C+ids 56/60. The identity table left 11 of 184 names waiting for a person; no question touched them, which is a gap in the test set, not a result.

## What was NOT chosen

| Alternative | Why rejected |
|---|---|
| Documents + chatbot only (A) | 18/60; 27 wrong numbers shown with real citations |
| AI-written SQL only (B) | 22/60; definitions and point in time don't live in the schema |
| Graph as the main engine (D everywhere) | No gain on routes or numbers at this size; adds a second copy of the data to keep in step |
| One front end for all three requests | The pack needs a fixed as-of date and export; the CIO needs a paragraph; the head of PE needs quotes |

## Consequences

**Enables:** the same number in chat, dashboard and notebook; refusals that name who can answer.
**Prevents:** free-form questions outside the metric menu.

## Open questions remaining

- [ ] Live run with `claude-sonnet-5-5`, same model and budget for all five setups, 3 reruns. Until then this ranking is a mechanism test. @PM
- [ ] Timed human run (design in the PRD). @PM

## Review trigger

Revisit if the live run moves any setup by 3 or more questions, or if a real portfolio shows routes deeper than 3 holdings.
