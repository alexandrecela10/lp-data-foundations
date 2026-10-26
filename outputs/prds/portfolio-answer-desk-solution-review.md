# Portfolio Answer Desk

**Stage:** Solution Review
**Last Updated:** 2026-10-25 (revised the same day: one Strategic fit section, metrics as tables, plainer words)
**Owner:** PM (drafted by Claude, unattended run approved by the PM)
**Status:** Reviewed, blockers fixed (see `portfolio-answer-desk-solution-review-review-synthesis.md`)

**What it is.** A question desk for the private equity team of a large investor. Sara, an analyst, types a senior leader's question. She gets back an answer she can send: the number, each way we own the company, the definition used, and the source and date of every figure. Inside sits a test that runs the same 60 questions through five ways of organising the data, and measures which gets Sara to a correct, sourced answer fastest. It can't read real fund reports or connect to a real accounting system yet: all data is synthetic.

**Terms in this document**
- **LP:** an investor, such as a pension fund, that commits money to many private equity funds.
- **Setup:** one way of organising the data plus the AI's job in it. We test five, A to D (table below).
- **Semantic layer:** a list of agreed calculations, each with one definition, one owner and a version. The AI picks one; code runs it.
- **Identity table:** a table saying that "Calderwick Holdings" and "Calder Packaging Ltd" are the same company.
- **Graph:** data stored as things and the links between them, so code can follow a chain of links (our LP, a fund, a company).
- **As of a date:** a number counts only what we knew on that date. A letter received 10 September doesn't change a 5 September answer.
- **Returns measures:** IRR (yearly return rate), TVPI (total value per dollar paid in), DPI (cash returned per dollar paid in).

---

## Hypothesis

Carried from `outputs/opportunity-analyses/portfolio-answer-desk-opportunity.md` (Go).

| # | Problem | Today | Hypothesis | Success metric (target) | Expected impact |
|---|---|---|---|---|---|
| 1 | A question about a company takes hours, because we own the company several ways, under several spellings | Unobserved (the brief says hours to a day; never timed) | If every spelling and holding is linked once in the data, then every way we own it is found in seconds, because code follows the links | Time to a correct, sourced answer Sara would send: under 10 minutes, 20 questions | Answer before the 09:00 meeting; unobserved |
| 2 | The committee pack changes from quarter to quarter, because each analyst computes returns and cash calls their own way | Unobserved | If each measure has one versioned definition computed as of a set date, then reruns and rewordings agree, because nobody rewrites the formula | Same answer on a rerun and a rewording: 100% of 20 questions | Fewer pack corrections; unobserved |
| 3 | A decision on a manager mixes numbers and letters, so problems get missed | Unobserved | If numbers come from the agreed definitions and problems from cited letters, then every known problem appears with its source | Known letter problems found with a citation: 100% | Fewer surprises at the decision; unobserved |

**Must not get worse:** wrong numbers shown with a source. Limit: zero on the 60 questions.

**Supporting evidence:** the brief's three requests and the Calder Packaging case (`context-library/strategy/brief.md`). No user research exists yet; every "today" value is assumed.

---

## Strategic Fit

- **Goal served:** the brief's goal (A), a measured prototype, and goal (B), plain-English teaching on graphs and semantic layers.
- **The value is fewer wrong numbers, more than time saved.** Time saved is about $43,000 a year for one LP, a quarter of one analyst (assumed; sizing in the opportunity analysis). That alone wouldn't justify agreeing definitions across teams. A leader deciding on 1 of 5 holdings instead of all 5 is the larger cost, and it isn't priced.
- **Build against buy, for a real LP:** buy the storage and dashboard software. Build the definitions, the company matching and the access rules, because no vendor ships them filled in. Assumed effort: 4 to 8 weeks to agree 10 core definitions and match company names.
- **Alternatives considered:** buy a portfolio monitoring product (rejected for the prototype: no access, and it hides the definitions we want to test); documents plus a chatbot only (kept as setup A, the thing to beat).
- **Request order:** request 1 first (most leadership attention), then 2 and 3 on the same data.
- **Confidence:** low. No observed baseline. De-risk with a timed test on 10 questions.

---

## Value Equation (Hormozi)

Carried forward from the opportunity analysis. Scope unchanged.

| Factor | This solution |
|---|---|
| **Dream outcome** | "I send the CIO a correct answer with every holding and source before 09:00, and it matches last quarter's pack." |
| **Perceived likelihood** | Low at first: chatbots invent numbers. Rises only if every number shows its source and date and the tool refuses instead of guessing |
| **Time delay** | Minutes per question once built; weeks to agree definitions and company links (assumed) |
| **Effort & sacrifice** | Sara asks in plain words. The data team gives up local spreadsheet formulas and owns one definition per measure |

**Verdict:** strong outcome, weak belief. Cheapest lever: show source and date on every number, and publish the test results.

---

## Non-Goals

- **Real data or real systems.** No access, and the names policy forbids it. Synthetic only.
- **Live streaming of data.** Measured in Secondaries Radar: daily or weekly loads were enough for a weekly decision. Each source here keeps a schedule and a date instead.
- **Forecasting returns.** The 12-month cash call forecast is a stated, versioned rule, not a model of how managers behave.
- **A graph-only setup (E).** Built only to time sums at scale, not to answer questions.
- **Not tackled:** reading real report layouts (synthetic report text only); people data beyond invented manager partners.

**Trade-off made:** in the offline tests, fixed rules stand in for the AI, so tests and the demo run with no key. The cost: offline A and B show what each setup can and can't do, not Claude's real error rate.

---

## Annex A, Napkin Sketch

### Screen 1, Ask (Calder Packaging, Monday 08:12)
**Job.** When the CIO asks about a company in the news, Sara wants every way we own it and the latest known value, so she can reply before 09:00.
**Main button.** "Copy answer to send".

```
+------------------------------------------------------------+
| Ask a portfolio question          as: Sara (analyst)       |
| [How exposed are we to Calder Packaging?            ] [Ask]|
+------------------------------------------------------------+
| $X.Xm held 5 ways, after the 10 Sep write-down.           |
|  1 Halvane V (fund)          $..m  report 30 Jun, letter   |
|  2 Selbrook FoF III > ...    $..m  report 30 Jun           |
|  3 Co-invest Calderwick Hold. $..m  statement 30 Jun      |
|  4 Tellmar III (bought 2024) $..m  report 30 Jun           |
| Definition: look-through exposure v2, owner Risk team      |
| Freshness: holdings 1 day, reports 118 days, letters 46 d  |
| [Copy answer to send]  [Show holdings on the graph]        |
+------------------------------------------------------------+
```

### Screen 2, Committee pack (Thursday)
**Job.** When the committee meets, Sara wants the 2019 to 2021 buyout funds against plan on last quarter's definitions, so the pack needs no rework.
**Main button.** "Export pack as of 30 Sep 2026".

```
+---------------------------------------------------------+
| Pack as of [30 Sep 2026]   definitions: pack v3 (same)  |
| Fund          Vint  Net IRR  Plan  TVPI  DPI  Unfunded  |
| ...                                                     |
| Calls next 12 months: $..m (rule calls-12m v2)          |
| [Export pack as of 30 Sep 2026]                         |
+---------------------------------------------------------+
```

---

## Solution Overview

**Five setups share one synthetic world.** Each request gets the screen that suits it.

| Setup | How the data is organised | What the AI does | What code does |
|---|---|---|---|
| A | Documents plus search | Reads the top passages and writes the answer | Searches report, letter, notice and news text |
| B | Tables, AI writes the database query | Writes a database query (SQL) from the list of tables | Runs the query, read-only |
| C | Tables plus a semantic layer | Picks an agreed calculation, filters and a date from a menu | Turns the pick into a query, checks access, computes |
| C+ids | C plus an identity table | Same as C | Same as C, and treats all spellings of a company as one |
| D | C+ids plus a graph and letter search | Same as C, and sends ownership and people questions to the graph | Follows ownership links and people links; searches letters |

C+ids exists to test whether the graph earns its place on ownership, not just on spellings. Offline, A and B get help so they aren't easy to beat: A's search also tries each company's other names; B gets prepared tables with column notes and parent links.

**Screens:** chat (request 1), a dashboard with 3 views (request 2), a briefing note (request 3), and a read-only SQL page for the data team.

**States designed:**
- **Refusal card:** what was asked, why it was refused, who can answer, and "Answer what I can see instead".
- **Waiting item:** "1 letter item not counted, waiting for review" under any total it affects.
- **Empty card** for a company we don't hold, and a banner when the offline stand-in answered.
- **Dates:** every holding shows its own date. A source older than 90 days reads "stale". The first line says "as of mixed dates" when dates differ.
- **Copy answer to send** copies the paragraph, holdings, sources, dates, Sara's note and the disclaimer.
- Every screen, copy and export carries "Synthetic data. Not investment advice."

**Data: six synthetic sources, each with its own rhythm and date.**

| Source | How often | Note |
|---|---|---|
| Holdings | Daily | |
| Capital calls and distributions | About weekly | Arrive as notice text |
| Quarterly fund reports | 45 to 90 days after quarter end | Each manager has its own layout and spellings |
| Manager letters | Whenever | Turned into dated events with a confidence; low confidence waits for a person |
| Company reference data | Rarely changes | Includes parent companies |
| News | Every 15 minutes | Never a source of numbers |

**Technology, chosen by measurement after the build** (decision docs in `outputs/decisions/`): recursive SQL for ownership chains, NetworkX for people links, our own YAML semantic layer, raw, cleaned and final tables in DuckDB 1.4.4 (bronze, silver, gold), and the AI picks while code computes.

---

## AI Behavior Contract

| Topic | Rule |
|---|---|
| **AI's jobs** | Send the question to the right path; turn the question into a calculation request; write the answer text around numbers code computed |
| **What it sees** | The question, the asker's role, and one of: the calculation menu (C, D), the table list (B), retrieved passages (A) |
| **Numbers** | Every number comes from code or a cited passage, inserted into the text by placeholders. A checker reads every number in the final text and refuses the answer if one wasn't computed. The AI never does arithmetic |
| **Access** | Each role sees its own copy of the tables; search drops documents the role can't see. The role picker is a demo switch, not a login |
| **Dates** | Every event has two dates: when it took effect and when we learnt of it. "As of D" counts only what we learnt on or before D |
| **Hosted demo** | Offline only, no key. Live calls only on a local run with a key, with the notice "Questions go to Anthropic. Do not enter real data." |
| **Never** | Numbers from news; numbers with no source; a calculation with no agreed definition; data the role can't see; real organisation names |
| **Model** | `claude-sonnet-5-5` when `ANTHROPIC_API_KEY` is set; an offline stand-in otherwise |
| **Speed, one answer** | Live: half of answers under 10 s, 95% under 30 s. Offline: under 1 s |

**Behavior examples:**

| Case | Sara asks | Expected answer | Why it refuses |
|---|---|---|---|
| Normal | "How exposed are we to Calder Packaging?" | Total, 5 holdings, the 10 Sep write-down applied, definition, date per number | |
| Other spelling | "What do we hold in Calderwick Holdings?" | Same company, same total; says "Calderwick Holdings is the holding company of Calder Packaging Ltd" | |
| Follow-up | "And excluding co-investments?" | Total minus the co-investment, same definition | |
| Earlier date | "As of 5 September, how exposed were we to Calder?" | No write-down applied: the letter arrived 10 September | |
| Refuse: role | "What fees do we pay on the Calderwick co-investment?" | Refusal; names who can see fee terms | Her role can't see fee columns |
| Refuse: no definition | "What's our PME against the index?" | Refusal; names the owner to ask | No agreed definition of PME (a return compared with a stock index) |
| Refuse: news number | "News says Calder's debt is $400m, what's our share?" | Won't use the news figure; offers exposure from our own data | News is never a source of numbers |

**If something fails:** a live call fails, so the offline stand-in answers and says so. A letter event with low confidence shows as "waiting for review" and isn't counted.

**How we test it:**
- 60 questions, 20 per request, with answers known from the data generator, traps included.
- Definitions written first, in `docs/DEFINITIONS.md`. The code that computes the right answers reads the generator only, never the setups.
- A second, held-out world (another seed, extra spelling noise the pipeline was never tuned on) is scored separately.
- The pytest gate guards the build (pipeline, access, disclaimer, number checker). It doesn't rank the setups; the live run does.

---

## Success Metrics

| Metric | What it measures | Target | How measured |
|---|---|---|---|
| **Time to a sendable answer (primary)** | From question to an answer Sara would send, including her checking time. A wrong answer fails, however fast | Under 10 minutes per question, winning setup | 60 test questions. Checking time is an assumed model: 20 s to read, 5 s per sourced number, 120 s per number checked by hand. Tested at half and double those times, and with 0%, 50% or 100% of sourced numbers rechecked. The timed test replaces it |
| **Correct answers** | Number within 0.5%, and every holding found | Ranked first, as counts out of 20 per request | Known answers from the generator |
| **Wrong numbers shown with a source (guardrail)** | A wrong number that looks trustworthy | 0 of 60 | Every answer checked against the known answer |
| **Same answer on a rerun and a rewording** | Whether the pack is stable | 100% on request 2 | 3 reruns live; reworded versions of each question |
| **Correct refusals** | Refuses traps, answers the rest | All 7 traps refused | Trap questions in the 60 |
| **Speed of one answer** | AI and code time, without checking | Live: half under 10 s, 95% under 30 s | Timed per answer |
| **Also reported, no target** | Cost per answer, data freshness, build effort (parts, lines of code), results at 10 and 100 times the data | | |

**Decision rules, set before any run:**

| Rule | Threshold | If not met |
|---|---|---|
| The graph earns its place | D beats C+ids by 2 or more correct on request 1, or by 2 or more minutes median time | Recommend C+ids; keep the graph for teaching |
| A live result counts | Every setup gets the same model, prompt budget and retries | The live result isn't used to rank |
| Build gate | D fails a question that isn't a trap, offline | The build is blocked |
| Chat stays | The AI picks the wrong calculation on 5% of live questions or fewer | Remove chat; keep the dashboard and briefing note |
| Demo goes live | No wrong number shown with a source, live | The demo stays offline only |

*Build gate changed 2026-10-25.* The original text said "C or D". C is the comparison point and is meant to fail on spellings, and the gate tests D only (`tests/test_eval_gate.py`).

---

## Rollout Plan

| Phase | What | Passing bar |
|---|---|---|
| 1 | Offline demo and committed test results | All tests pass with no key |
| 2 | Live test with `claude-sonnet-5-5`, run locally by the PM (one command) | Guardrail holds; live result counts (rule above) |
| 3 (next, before any headline is published) | Timed test with 3 to 5 former LP analysts | Checking-time model refitted from what they did |

**Timed test design:** three ways (by hand with documents and spreadsheets, setup A, the winner), in a different order per person; an equally hard but different company for each way; questions from all three requests; one practice session first. Record time to "send", numbers reopened, correct or not, would send (yes or no), and confidence from 1 to 5.

**Rollback:** if the live run breaks the guardrail, the demo stays offline only.

---

## Risks and Recovery

| Risk | How we'd see it | Fallback | Owner |
|---|---|---|---|
| The assumed checking time decides the ranking | Ranking changes at half or double the per-number times | Report correctness separately from time | PM |
| Offline stand-ins for A and B flatter C and D | Live results differ from offline | Publish live next to offline; label offline as a test of what each setup can do | Engineering |
| Right answers come from the same generator the pipeline reads | The code for right answers is a separate path | A test checks it imports nothing from the setups | Engineering |
| Synthetic letters are easier to read than real ones | Not detectable here | Stated in Limitations | PM |

---

## Open Questions

- [ ] Who runs the timed test, and can 3 to 5 former LP analysts take part? @PM
- [ ] Should the case study headline wait for the live run? Recommendation: yes. @PM
- [ ] Keep setup E for scale timing only? Recommendation: yes. @PM
- [ ] Which team owns look-through exposure (our share of a company across every fund and deal) in a real LP: risk or investment? @PM (synthetic owner: Risk team)

---

## Appendix: challenges to the brief (written down, as the brief asks)

1. **The main metric depends on an assumed checking time.** A setup that shows sources wins partly by design. We publish a sensitivity table and report correctness on its own.
2. **Offline A and B use fixed rules in place of an AI.** They show each setup's limits, not Claude's error rate. Live results are a separate, labelled run.
3. **"A graph for company identity" mixes two jobs.** Matching spellings is a lookup an identity table can also do. We test C+ids, so the graph has to earn its place on ownership, not only spellings.
4. **20 questions per request is small.** One question moves a score by 5 points. We report counts, not only percentages.
5. **The forecast and plan figures are rules, not truth.** For the cash call forecast, "correct" means "matches the agreed rule as of the date". That tests consistency, not foresight.

**Name check.** Options: "Portfolio Answer Desk" (answers leaders' portfolio questions, with sources), "Look-Through Finder" (too narrow: only exposure), "LP Question Bench" (names the test, not the job). Picked: **Portfolio Answer Desk**. The test inside is called "Foundation test".
