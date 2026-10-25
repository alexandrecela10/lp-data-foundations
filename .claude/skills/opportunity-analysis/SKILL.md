---
name: opportunity-analysis
description: A short, go/no-go gate before any PRD gets written, problem statement, current situation with one concrete pain example, proposed solution, hypothesis, and a Hormozi Value Equation gut-check on whether the people it's for would actually want it. Condensed from Marty Cagan's Opportunity Assessment (INSPIRED, 10 questions there, 4 plus a gut-check here). Runs after clarifying questions, before /prd-draft. Use when a PM has an idea and needs to decide whether it's worth a PRD at all, not when the PRD is already approved and in motion.
user-invocable: true
disable-model-invocation: false
---

# /opportunity-analysis: Opportunity Analysis

When the PM types `/opportunity-analysis`, run the gate: clarifying questions → a short opportunity doc → an explicit Go / No-go / Parked call.

**What this is not:** a PRD. It's cheaper and comes first. A PRD costs six sections and often a full review loop, most ideas don't deserve that yet. This decides whether an idea deserves the PRD at all, condensed from Cagan's ten-question Opportunity Assessment (*INSPIRED*) down to four questions plus one value gut-check, because most PMs don't need the full ten to make a call.

**Where this sits:** clarifying questions → **opportunity analysis (this)** → `/prd-draft` → `/prd-review-panel` or `/prd-graph`. `/prd-draft` checks for an approved opportunity analysis before drafting (see that skill's Step 0) and skips re-asking anything already answered here.

---

## Quick Start

```
/opportunity-analysis [rough idea or problem]   → Clarifying questions, then draft
/opportunity-analysis --skip-gate               → PM says this idea is obviously worth a PRD; skip straight to /prd-draft instead
```

---

## Context Routing

Same sources as `/prd-draft`: `context-library/business-info*.md`, `context-library/strategy/`, `context-library/research/`. Also check `outputs/opportunity-analyses/` (or this project's own override path, see Step 3) for an existing draft on this feature before starting fresh; don't duplicate one that already exists.

---

## Tone & Audience (added 2026-09-07, PM correction)

**Default reader is the decision-maker, not an engineer.** The entire point of an opportunity assessment (Cagan) is to get someone who can say go/no-go to actually say it, usually the founder/exec, not an engineering peer who'll read the PRD later. Write for them by default:

- **No inline citations.** State facts plainly and confidently, this is a business document, not a technical one. Keep a single compact **Sources** line at the very bottom (file paths only, no prose) so facts stay checkable without cluttering the read.
- **Lead with problem, hypothesis, and value.** State what must change before how it might be delivered. Cut anything that only makes sense to someone who's read the codebase; that belongs in the PRD, not here. Keep tools, channels, architecture, data sources, and build-versus-integrate choices out of the opening and Proposed Solution unless one is already decided.
- **Show the pain as atomic problems (added 2026-10-04, PM correction).** One table, one row per atomic problem: Today, hypothesis, one success metric with a target, expected impact. It replaces a separate before/after table, sub-problem list and hypothesis section. Never list the same problems twice.
- **Visualize the proposed solution, 1-2 screens max, when there's something to show.** Strip engineering framing (no JTBD/CTA labels), just the picture and a one-line caption. If a PRD or prior sketch already exists for this feature, simplify from that instead of drawing fresh.
- **Stay factual.** Exec tone doesn't mean softer claims, it means the same facts, stated more directly, with the paper trail moved to a footnote instead of paraded inline.

**Switch to technical mode**, inline citations return, visuals become optional rather than default, when the actual reader is an engineer assessing feasibility, not a business decision-maker assessing priority. Signal: `--technical`, or the PM says who this is really for.

This is the same "by audience" principle already stated generally in PM-OS's root `CLAUDE.md` (Internal/Exec/Technical/User-facing), wired into this skill's actual default behavior rather than left as a reminder to apply manually each time.

---

## Workflow

### Step 1: Clarifying questions (adaptive, same rule as `/prd-draft`)

Check what the PM already gave you before asking. Skip anything context-library or the prompt already answers. Ask only the gaps, and only these four:

1. **What problem, precisely**, not a category? (the pain, not the fix)
2. **Who feels it, and how do you know**, an observed pain, or an inferred one? (Be honest here, "I read the code and inferred this" is a real, valid answer, just a weaker one than "a user told me")
3. **What's the current workaround today, and what's actually wrong with it?**
4. **What must change for the user or business**, one sentence? Define the needed capability or outcome, not the implementation.

Confirm the brief back in one paragraph before drafting. Don't skip this, everything downstream depends on it being right.

### Step 2: Draft

Use exactly this structure. Target **under ~300 words** outside the Value Equation table and Recommendation, if it's creeping toward PRD length, that's the tell that this is the wrong output for this step; stop and cut.

```markdown
# [Idea name]: Opportunity Analysis

**Date:** [date]
**Owner:** [name]
**Status:** Draft / Go / No-go / Parked

## Problem Statement

[One or two sentences. The pain, not the feature. No category language, "users want a better experience" is not a problem statement. Plain English, no jargon a founder wouldn't use.]

## Current Situation

[What happens today, in one or two plain sentences, no jargon, no code-level detail.]

**A concrete case.** [One named instance of the pain, real if you have one, a labelled hypothetical if you don't. Not an abstract persona. This is the most important paragraph in the document: if you can't write a concrete example, the problem probably isn't real yet, and that's worth knowing before a PRD gets written, not after.]

## Proposed Solution

[Say what the solution is and what it does: one capability per tackled problem, and for whom. For an AI product, name the kind of AI in plain words (e.g. "a language model, an AI that reads and writes text"), what it does, and what checks its work. Not the vendor. The outcome belongs in the Problem and Expected impact columns, not here (added 2026-10-04, PM correction). Do not lead with a page, tool, channel, architecture, data source, or build-versus-integrate choice. The PRD is where the implementation gets specified.]

## Problems, hypotheses and success

[One row per atomic problem: one job, one hypothesis, one metric. If success needs two metrics, split the row. Mark "Today" values assumed or observed.]

| # | Problem | Today | Hypothesis | Success metric | Expected impact |
|---|---|---|---|---|---|
| 1 | [one atomic problem, the pain not the fix] | [what happens now; observed or assumed] | If [change X], then [observable Y], because [mechanism Z] | [one metric]: [target] | [what changes for the user or business; direction + value, or "unobserved"] |

**Must not get worse:** [one guardrail metric and its limit]

**Not tackled here:** [untackled atomic problems, one line each, with what's missing]

## How It Could Be Delivered (optional; include only when useful for the decision)

[Put pages, tools, channels, architecture, data sources, build-versus-integrate options, and 1-2 simplified visuals here. Keep undecided choices explicitly open. Reuse and simplify an existing sketch when one exists.]

## Value Equation (Hormozi)

> Adapted from Alex Hormozi's Value Equation (*$100M Offers*): Value = (Dream Outcome × Perceived Likelihood of Achievement) / (Time Delay × Effort & Sacrifice). Built for a customer with a choice not to buy, for an internal tool, read "would they actually use it" wherever it says "would they buy it." A gut-check on desirability, not a technical feasibility check.

| Factor | This solution |
|---|---|
| **Dream outcome** | [what does success feel like for them, in their own words, not a feature description] |
| **Perceived likelihood** | [will they believe, before they've used it, that this will actually deliver, high skepticism kills adoption even when the solution is good] |
| **Time delay** | [how long until they feel the benefit, from the moment it ships] |
| **Effort & sacrifice** | [what do they have to do, learn, or give up to get the benefit, a new habit, a new tab to remember, a workflow change] |

**Verdict.** [Strong or weak ratio, and if weak, name the *cheapest lever*: raising belief, cutting delay, or cutting effort is usually cheaper than improving the outcome itself. Don't skip straight to "make the outcome better."]

## Recommendation

**Go / No-go / Parked, one sentence why.** If Go: proceed to `/prd-draft`. If No-go or Parked: name the specific thing that would change the answer, so this isn't a dead end.

## Open Questions

[Only what's genuinely unresolved and blocks the Go/No-go call itself, not a general punch list. If nothing blocks the call, leave this section out.]
```

### Step 3: Save + companion files

Save to `outputs/opportunity-analyses/[feature-name]-opportunity.md`, **unless this project's own `CLAUDE.md`/`AGENTS.md` overrides the output path**, in which case that wins (check it first; don't default blindly to `outputs/`).

Per the standing rule (added 2026-09-06, `{pm-os}/CLAUDE.md`): every output ships with its success criteria and a decision record. Draft both alongside this doc:
- A short **goals file** (`[feature-name]-opportunity-goals.md`): 3-5 binary criteria, e.g. "the Example paragraph names something concrete, not a category or abstract persona"; "all four Value Equation factors are filled, none left as a placeholder"; "the Recommendation states Go/No-go/Parked explicitly."
- A **state file** (`[feature-name]-opportunity-state.json`): the recommendation made, why, and what would change it, so the next session doesn't re-litigate a call that was already made.

### Step 4: Report the call and handoff

State the Go / No-go / Parked recommendation plainly, not buried in prose. If Go, offer to run `/prd-draft` next, it reads this file automatically (Step 0 of that skill) and won't re-ask what's already answered here; the Value Equation carries forward into the PRD rather than getting re-derived from scratch.

---

## Integration with other skills

**Before this:** the adaptive clarifying-questions rule (check `context-library/` before asking anything).

**After a Go:** `/prd-draft`, reads this file, skips duplicate questions, carries the Value Equation forward.

**Not a replacement for `/impact-sizing`.** This is qualitative (should we even look at this?); `/impact-sizing` is quantitative (funnel math, driver trees) and belongs later, typically at Planning Review, once the opportunity has already cleared this gate. Running impact-sizing before an opportunity analysis is solving the wrong problem first.

**Not a replacement for `/prd-review-panel` or `/prd-graph`.** Those review a PRD that already exists. This decides whether one should exist.

---

## Output Quality Self-Check

Before presenting the draft, first run the root `CLAUDE.md` Voice check: no em dashes anywhere in the document, no unearned superlatives (instant, seamless, powerful), no sales-style reassurance ("with confidence," "no more guessing"). This document is exec-facing by default, which raises the temptation to sell rather than inform. Resist it. Then check:

- [ ] Under ~300 words outside the Value Equation table and Recommendation, if it reads like a PRD, cut it back down
- [ ] No inline citations (unless technical mode), facts stated plainly, with a single Sources line at the bottom so they're still checkable
- [ ] The concrete case names something real (a real incident, or a labelled hypothetical), never an abstract persona
- [ ] The Proposed Solution says what the solution is and does (one capability per tackled problem; for AI, the kind of AI and what checks it), not the outcome, and not a page, tool, channel, architecture, data source, or build-versus-integrate choice
- [ ] Any unresolved implementation options appear later under "How It Could Be Delivered" or Open Questions, not in the opening or Proposed Solution
- [ ] Every fact is true and checkable via the Sources line, exec tone is not permission to soften or invent a claim
- [ ] Problems appear once, in one table: each row is one atomic problem with one hypothesis and one metric with a target, plus one "must not get worse" line
- [ ] The solution sketch, if included, is 1-2 screens max with engineering framing (JTBD/CTA) stripped out
- [ ] All four Value Equation factors are filled in, no placeholder text left in
- [ ] The Recommendation is an explicit Go / No-go / Parked, never left implicit or hedged into "it depends"
- [ ] Saved to the project's actual output location (checked for a per-project override first)
- [ ] A companion goals file and state file exist alongside it
