# User Journey Map: Sara answers three requests

**Persona:** Sara, portfolio analyst, private equity team of a large LP (synthetic: Aldermoor Pension Plan). Asked by the CIO's office, the investment committee and the head of private equity.
**Goal:** send each asker a correct, sourced answer, fast, on agreed definitions.
**Duration:** request 1 in minutes (Monday morning); request 2 over two days (Thursday pack); request 3 over a week (re-up decision).
**Mode:** user journey map. No user research exists: thoughts and emotions are hypotheses, every time is assumed or "unobserved", and no quote is a real user's.

**Rule applied:** every phase ends with something Sara decides or does. Phases where only the system works are folded into the phase they support.

---

## Overview

```
Request 1 (CIO, Mon 08:12)   Ask ──▶ Check routes ──▶ Check "did we know" ──▶ Send
Request 2 (Committee, Thu)   Set date ──▶ Review pack ──▶ Explain changes ──▶ Export
Request 3 (Head of PE)       Ask history ──▶ Read issues ──▶ Hand over note
```

---

## Request 1: an event (chat)

### Phase 1.1: Ask
**Duration:** 1 minute | **Goal:** turn the CIO's message into a question

| Element | Details |
|---|---|
| **Touchpoints** | News alert 08:10 ("Calder Packaging restructuring its debt"), CIO email 08:12, chat box |
| **Actions** | Pastes "How exposed are we to Calder Packaging, and to European packaging? Through which managers? Did we know?"; **decides** the as-of date (default today) |
| **Thoughts** | "Is the news number usable? No, I need our own data." |
| **Emotions** | 😟 Pressed: meeting at 09:00 |
| **Pains** | 🔴 Today she starts by searching folders by hand. 🟡 The news gives a debt figure she can't use |
| **Opportunities** | 💡 Refuse the news figure out loud and offer exposure from governed data (behaviour contract row "news number") |
| **Metrics** | Time to first answer: under 1 s offline (measured in eval), live unobserved |

### Phase 1.2: Check the routes
**Duration:** 2 to 4 minutes | **Goal:** trust the total

| Element | Details |
|---|---|
| **Touchpoints** | Answer card: total, route table (each route with its as-of date), "Show routes on the graph" with a "Next hop" button |
| **Actions** | Opens each route's source passage; **decides** whether each route belongs (a fund of funds stake counts; a news mention does not) |
| **Thoughts** | "Calder Pack. and Calderwick Holdings: are those the same company?" |
| **Emotions** | 🤔 Unsure → 😊 relieved when the card says "Calderwick Holdings is the holding company of Calder Packaging Ltd" |
| **Pains** | 🔴 Spellings hide routes. 🟡 A 30 June report looks like today's number |
| **Opportunities** | 💡 Mark "as of mixed dates" and "stale" on sources over 90 days. 💡 Show which spelling linked to which company, and how sure the match is |
| **Metrics** | Routes found out of 5 (eval, per foundation) |

### Phase 1.3: Check "did we know"
**Duration:** 1 minute | **Goal:** answer the CIO's hardest question honestly

| Element | Details |
|---|---|
| **Touchpoints** | Event line: write-down on 2 September, learnt 10 September from the manager's letter; a 28 July concern "waiting for review" |
| **Actions** | **Decides** whether to mention the July concern (shown as not counted, with its quote) |
| **Thoughts** | "If I say we knew in July, is that fair? It was only a worry, not a write-down." |
| **Emotions** | 😐 Careful |
| **Pains** | 🔴 Today the write-down sits only in a letter nobody linked to the holdings |
| **Opportunities** | 💡 Show both dates for every event: when it happened and when we learnt it |
| **Metrics** | "Learnt on" date correct (eval) |

### Phase 1.4: Send
**Duration:** 1 minute | **Goal:** reply before 09:00

| Element | Details |
|---|---|
| **Touchpoints** | "Copy answer to send": paragraph, routes, definitions, as-of dates, disclaimer; optional note |
| **Actions** | Adds a note ("July concern not counted"), **sends** |
| **Emotions** | 😊 In control |
| **Opportunities** | 💡 One-line CIO version above the detail |
| **Metrics** | Main metric: time until a correct, sourced answer she would send (eval, assumed checking-time model) |

---

## Request 2: the committee pack (dashboard)

### Phase 2.1: Set the date and definitions
| Element | Details |
|---|---|
| **Touchpoints** | Dashboard, as-of picker (30 Sep 2026), definitions banner "same as last quarter's pack, except unfunded v2" |
| **Actions** | **Decides** the as-of date and whether to accept a changed definition or pin last quarter's |
| **Thoughts** | "If unfunded changed, the committee will ask why the number moved." |
| **Emotions** | 😟 Wary of surprises |
| **Pains** | 🔴 Today each analyst's spreadsheet computes IRR, TVPI and calls its own way |
| **Opportunities** | 💡 Show what changed since last pack, with the reason |
| **Metrics** | Same answer on rerun and rephrasing (eval) |

### Phase 2.2: Review the funds against plan
| Element | Details |
|---|---|
| **Touchpoints** | View 2 "Funds against plan": 2019 to 2021 buyout funds, net IRR, TVPI, DPI, plan, unfunded |
| **Actions** | **Flags** funds behind plan for discussion |
| **Emotions** | 😐 Routine |
| **Pains** | 🟡 Manager-reported IRR differs from our own cash-flow IRR (credit lines, purchase price on second-hand stakes) |
| **Opportunities** | 💡 Show the manager's figure next to ours, labelled, never mixed |

### Phase 2.3: Explain the calls forecast, then export
| Element | Details |
|---|---|
| **Touchpoints** | View 3 "Cash next 12 months", rule "calls-12m v2" in plain words |
| **Actions** | **Exports** the pack as of 30 Sep 2026 |
| **Emotions** | 😊 Done early |
| **Metrics** | Export carries definitions, versions and the disclaimer (test) |

---

## Request 3: a relationship decision (briefing note)

### Phase 3.1: Ask for the history
| Element | Details |
|---|---|
| **Touchpoints** | Briefing note page: "Brennick Capital Partners is raising Fund VI" |
| **Actions** | **Picks** the manager and the as-of date |
| **Emotions** | 😐 |
| **Pains** | 🔴 Today: numbers in one place, letters in another, people links in someone's head |

### Phase 3.2: Read the issues
| Element | Details |
|---|---|
| **Touchpoints** | Note sections: commitments, results fund by fund, co-investments, issues from letters (each with a quote and date), people moves |
| **Actions** | **Decides** which issues the head of PE must read first |
| **Thoughts** | "A partner left in 2024: did she join another of our managers?" |
| **Emotions** | 🤔 Curious → 😊 when the note shows she joined Wexcombe Growth Partners |
| **Pains** | 🔴 An issue phrased loosely (a fee offset) is missed by a fixed extractor |
| **Opportunities** | 💡 Search every letter, cite each hit; refuse to show co-investment fee terms to her role |
| **Metrics** | Planted issues found with a citation, out of 5 (eval) |

### Phase 3.3: Hand over
| Element | Details |
|---|---|
| **Actions** | **Sends** the note to the head of PE, who can see the fee terms she can't |
| **Emotions** | 😊 |

---

## Summary

### Biggest pain points
1. 🔴 Routes hidden behind spellings and hops (Request 1, Phase 1.2)
2. 🔴 Definitions that drift between packs (Request 2, Phase 2.1)
3. 🔴 Issues buried in free text (Request 3, Phase 3.2)

### Top opportunities
1. 💡 Identity links plus a route walk, shown as a numbered route table with a graph picture: improves routes found
2. 💡 One versioned definition per metric with a "changed since last pack" banner: improves same-answer rate
3. 💡 Search with citations for letters, structured numbers for everything else: improves issues found with a source

### Emotional journey
```
😟 Pressed → 🤔 Unsure → 😊 Relieved → 😐 Careful → 😊 In control
[1.1 Ask]   [1.2 Routes] [identity]   [1.3 Knew?]  [1.4 Send]
```

### Next steps
- [ ] Build the refusal card, "waiting for review" line and stale badges (PRD review fixes)
- [ ] Timed human run to replace every assumed time on this map
- [ ] Three interviews with analysts about a recent real ad hoc question
