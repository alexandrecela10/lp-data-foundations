---
decision_id: "PAD-05"
date: "2026-10-25"
product_area: "Measurement"
feature: "Portfolio Answer Desk"
prd_stage: "Solution Review"
decided_by: "Claude (unattended run); PM to ratify"
status: "active, assumption"
---

# Decision: Measure "time to a sendable answer" with a stated checking-time model, and publish how the ranking moves when it changes

## What was decided

Time to a sendable answer = answer time + Sara's checking time. Answer time = measured compute + an assumed 3 s per AI call (offline). Checking time (assumed, in `src/answerdesk/answer.py`): 20 s to read; 5 s per number with a source and a governed definition; 30 s with a source only; 120 s by hand; 5 s or 60 s per listed item with or without a source; 50 s for a correct refusal. A wrong answer is a fail; in the expected time per question it costs 2 hours of manual work (assumed).

## Why

The brief asks for it, and it is the metric that matters to Sara. It can't be measured without people, so it is a model until the timed run.

## The measured trade-off (offline, 60 questions)

| Setup | Correct | Median time, correct answers only | Expected time per question (fails = 2 h) |
|---|---|---|---|
| A documents + search | 18 | 51 s | 84 min |
| B AI-written SQL | 22 | 86 s | 77 min |
| C semantic layer | 41 | 28 s | 38 min |
| C+ids | 56 | 33 s | 8.6 min |
| D | 60 | 33 s | 0.7 min |

**Sensitivity** (`sensitivity` in the results file): halving or doubling the per-number times keeps the order C < C+ids = D < A < B on median time. If Sara rechecks 50% of sourced numbers by hand, A becomes fastest on median time (51 s against 86 s) because it shows fewer numbers. **So the time advantage depends on Sara trusting a shown source; the correctness advantage (60 against 18) does not.** Median time over correct answers flatters C, whose correct answers are the easier ones; the expected time per question doesn't.

## What was NOT chosen

| Alternative | Why rejected |
|---|---|
| Report only latency | Ignores checking, which dominates (seconds of compute against tens of seconds of reading) |
| Invent a measured baseline ("hours") | Never timed; the brief's "hours to a day" stays unobserved |

## Review trigger

Replace the model with the timed human run (3 to 5 former LP analysts, three arms, counterbalanced; design in the PRD, Rollout Phase 3).
