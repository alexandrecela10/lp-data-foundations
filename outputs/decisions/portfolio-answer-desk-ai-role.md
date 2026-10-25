---
decision_id: "PAD-03"
date: "2026-10-25"
product_area: "AI behaviour"
feature: "Portfolio Answer Desk"
prd_stage: "Solution Review"
decided_by: "Claude (unattended run); PM to ratify"
status: "active"
---

# Decision: The AI picks a governed metric; code computes every number; a checker blocks any number we didn't compute

## What was decided

In the shipped combination the language model only reads the question into fixed fields (metric, company, dates, filters). Code computes. The answer text uses the computed numbers in placeholders, and `answer.guard` extracts every number from the final text and withholds the answer if one isn't in the computed or cited set.

## Why

- **Measured:** wrong numbers shown with a source, out of 60 questions offline: documents + search (A) 27, semantic layer (C) 15, C+ids 2 before it gained letter search and 0 after, D 0 (`evals/results/offline-seed42.json`). A's are the dangerous kind: a fund of funds' look-through line multiplied by our share of the fund of funds, shown with a real citation.
- **Live** (`evals/results/live-claude-sonnet-5-5.json`, `claude-sonnet-5-5`): A 7 wrong numbers with a source, B 0, C 15, C+ids 0 (after it gained letter search), D 0. Where Claude only filled in the question's fields (C, C+ids, D), every score matched offline and the rerun gave the same answer on all 60 questions. Where Claude also read passages (A) or wrote SQL (B), A fell from 18 to 7 correct and B from 22 to 11; the number checker withheld many of A's answers ("number check failed").
- **Example and counterfactual.** The AI picks `lookthrough_exposure` for Calder Packaging; code returns \$8.06m from 5 routes. Had the AI written the number itself, \$8.1m and \$81m would read the same to the checker of a chat window; here a number not in the computed set fails closed (`tests/test_governance.py::test_number_checker_fails_closed`).

## What was NOT chosen

| Alternative | Why rejected |
|---|---|
| AI reads documents and writes the answer (A) | 18/60 correct offline, 7/60 live; 27 and 7 wrong numbers with citations |
| AI writes SQL (B) | 22/60 offline, 11/60 live; same answer on a rerun for 80% of questions live; misses what the schema doesn't say (when a report arrived, write-downs in letters, recallable distributions, the call forecast rule) |

## Consequences

**Enables:** refusals that name who can answer; every number traceable to a bronze document.
**Prevents:** open-ended questions outside the metric menu; they are refused, not guessed.

## Open questions remaining

- [x] Live run with `claude-sonnet-5-5` done (2026-10-25): 960 calls, 0 failed, \$6.25, 47 minutes. A first attempt the same day was invalid: the question schema had 18 nullable fields, the API's limit is 16, and every live read fell back to the offline reader without saying so. Fixed: no nullable fields, and any failed live call now marks the run invalid.

## Review trigger

If the live run shows the AI picking the wrong metric on more than 3 of 60 questions, remove the chat front end and keep the dashboard and briefing note.

**Checked 2026-10-25:** D, which uses the same live reader, answered 60 of 60 live, so no wrong pick changed an answer. Chat stays.
