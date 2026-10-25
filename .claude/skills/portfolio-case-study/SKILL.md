---
name: portfolio-case-study
description: Turn a finished project into a public case study page (portfolio hub on GitHub Pages) plus a LinkedIn project entry, for a private capital audience, written to the visitor as "you". Hero with outcome headline, stat strip and demo link; then 7 short sections (vision, problem, solution, job/hypothesis/metric/impact table, value, limitations, non-goals and next); everything else collapsed, including the full opportunity assessment and PRD when they exist. Minimal factual tone. Runs /name-audit first and checks every claim against code, logs and tests.
user-invocable: true
disable-model-invocation: false
---

# /portfolio-case-study

Input: a project folder or repo path. Output: `outputs/portfolio/<slug>/` with `index.html`, `linkedin.md`, `name-audit.md`, plus a goals file and a state file (see CLAUDE.md).

## Steps

1. **Read the source, then the code and its outputs.** README, demo script, decks, code, logs, test suite, generated files. Keep observed numbers only.
2. **Check claims.** Every README or deck claim is checked against code, logs or tests. Example: a README said "no LLM call"; the log showed one. Wrong claims are corrected, not repeated.
3. **Map atomic problems to code.** For each atomic problem (one job, one hypothesis, one metric): tackled, partial or not tackled, with the file or function that proves it.
4. **Run `/name-audit`.** No repo edit before the PM approves its list.
5. **Draft from `template.html`** (in this folder), following the page structure below. Collect the opportunity assessment, PRD or delivery deck to embed. Same order in `index.html` and `linkedin.md`.
6. **Check links.** Every link returns 200. A sibling page that doesn't exist yet reads "case study coming", with no link.
7. **Checks.** Tone rules in CLAUDE.md (minimal factual, no em dashes, banned words, factual over persuasive). LinkedIn description 2,000 characters or fewer (`wc -m`). Every number traces to a source or reads "unobserved".
8. **Goals + state files.** Wait for PM approval before any repo edit, push or publish.

## Page structure (added 2026-10-10, PM correction: the Data Room Check pattern)

Reference page: `outputs/portfolio/data-room-check/index.html`. Every case study uses this structure. Write to the visitor as "you" throughout: the lede, the value cards, the jobs.

**Hero:**

| Block | Content |
|---|---|
| Eyebrow | "Case study · <asset class> · <stage or tech>" |
| Headline | The outcome for the user, one sentence. Not the feature |
| Lede | "You're a <role> at a <private capital player>. <the problem in one line>. <Name> <does what>." |
| Buttons | Try the demo (primary), Code, deck or video. One line labelling real vs fictional data |
| Stat strip (value metrics, added 2026-10-25, PM correction) | 4 observed numbers that prove the value offer, not the technique: productivity (time per task, tasks handled), deals or items processed, decision quality (good pricing, good deals kept, errors caught), groundedness (share of claims traced to a source), cost. Technical metrics (match accuracy, precision, recall, test counts) are means to an end: they go in section 04, the learnings or the eval resource, never the hero. Each label says what you gain, with its baseline when there is one. No design facts presented as results |
| Glance | For (the player), Users (you + the buyer, with the decision each owns), Data, Built with |
| Techniques (added 2026-10-10; tightened 2026-10-25, PM correction) | One row of pills showing the technical craft, 4 to 6 pills, each tagged AI, Data eng or Data science. Each pill is 2 to 6 plain words naming what the technique does ("Recognises funds by their numbers"), not a tool list. **No Eval pills:** evaluation is expected on every project, so it goes in the "How it's built" resource, not the hero. Every pill traces to the code or the page |

**Main page: 7 numbered sections, short, in this order:**

| # | Section | Content |
|---|---|---|
| 01 | Vision | One-sentence heading, then today vs the vision in 2 to 3 sentences |
| 02 | The problem | One card per tackled atomic problem. Card label states the outcome for you; the text states the cause |
| 03 | The solution (concise, 2026-10-25, PM correction) | Three short cards: **What it is** (one sentence naming the kind of product a buyer recognises, e.g. "a triage assistant for secondaries offers", "a proactive outbound finder"), **What it does** (one or two sentences: input and output), **What you get** (the decision it improves and how, e.g. "faster, better-informed choice of which offers go to the NDA stage"; to the visitor as "you"). Heading names the split, e.g. "The AI reads. Code checks. You decide." No step list here: the step-by-step build goes in the "How it's built" resource |
| 04 | Hypotheses and impact | One table, one row per tackled problem: Your job ("When I…, I want…, so…") / Hypothesis (if, then, because) / Metric and target, then result / Expected impact (direction, value or "unobserved"). One "must not get worse" line under it |
| 05 | The value | One pull quote with the money or time at stake (label illustrative numbers). One card per persona: You get / Will you believe it? / How fast / What it takes / What you give up, each with a rating. Close with the weakest factor and the cheapest fix |
| 06 | Limitations | What this doesn't prove yet: data, users, accuracy, assumptions |
| 07 | Scope and next steps | Two cards: Non-goals (incl. untackled problems) and Next (numbered tests or builds) |

**Resources ("Go deeper."), all collapsed `<details>`, each summary with a one-line hint:**

1. Try the demo, step by step (3 numbered steps in the you frame), unless the demo guides the journey itself
2. Main learnings (observed in the build, with which hypothesis each supports)
3. Hypotheses in full (before → after, test per problem)
4. All sub-problems (tackled, partial, not tackled, with the code that proves it)
5. How it's built (input → process → output); how it was evaluated if there is an eval
6. How success is tracked (leading and lagging metrics)
7. Scope table and trade-offs table (chose, over, gain, cost)
8. Terms on this page
9. **Source documents, in full, when they exist:** the opportunity assessment and the PRD rendered from markdown. If the project used another format (e.g. a delivery deck), embed that instead. Never write a stand-in document. Apply the name-audit replacements and the house writing rules to the embedded copy only, and say so in a note
10. Related project and links
11. How it was built with PM OS (lifecycle table, then PM OS skills used)

## Demo (added 2026-10-05, PM correction)

- **Write to the visitor as "you".** Second person on every screen: "You're an analyst at a family office. Pick the deck you want to check." Never third person ("what the analyst sees").
- **Guide a journey.** Numbered steps, one "Next" button per step, and a sidebar showing where the visitor is.
- **Sample first, then theirs.** Open on a sample input the visitor can look at, then let them change it or bring their own.
- **Same rule on the case study page.** Any "Try it" copy that describes the demo uses "you".

## Writing style

Follow **Minimal factual** in CLAUDE.md for every section. Tables and lists for parallel items, sentences for reasoning.

**Plain English throughout (added 2026-10-25, PM correction).** Write every section, resources included, for a smart reader outside finance and outside engineering: everyday words, sentences of about 20 words or fewer, one idea each. Replace jargon ("held-back set", "lineage", "fingerprinting", "overfitting") with what it means ("test offers the rules never saw", "every number traced to its source"). Keep a domain term only when the user really says it, and explain it in brackets the first time. Apply `outputs/portfolio/plain-language-rules.md` in full.

## Page design

Copy `template.html` from this folder: the Data Room Check layout. Navy background, blue accent, Lato: matches the LinkedIn banner. Numbered section labels in the accent colour, card grids that stack on mobile, ratings in heavy white, wide tables wrapped in `.scroll`. Check at 420 px and 1280 px: no horizontal scroll.

## LinkedIn entry

Same order, compressed. Name, one line, problem, player, demo link, then one line per hypothesis. 2,000 characters max.
