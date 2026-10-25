# Portfolio Answer Desk

**Stage:** Solution Review
**Last Updated:** 2026-10-25
**Owner:** PM (drafted by Claude, unattended run approved by the PM)
**Status:** In Review

**What it is.** A portfolio question desk for the private equity team of a large LP. Sara types or picks a question from a senior leader; she gets back a sendable answer: the number, the routes behind it, the definition used, the source and as-of date of every figure. Inside it sits a test bench that runs the same 60 questions through four data foundations and measures which gets Sara to a correct, sourced answer fastest. It can't yet read real fund reports or connect to a real accounting system: all data is synthetic.

---

## Hypothesis

Carried from `outputs/opportunity-analyses/portfolio-answer-desk-opportunity.md` (Go).

| # | Problem | Today | Hypothesis | Success metric | Expected impact |
|---|---|---|---|---|---|
| 1 | An event question takes hours because the company hides behind several routes and spellings | Hours (assumed, from the brief) | If routes and spellings are linked once in the data, then every route is found in seconds, because code walks the links | Time to a correct, sourced answer Sara would send, request 1: under 10 minutes, 20 questions | Answer before the 09:00 meeting; unobserved |
| 2 | The committee pack drifts because each analyst computes IRR, TVPI and calls their own way | Unobserved | If each metric has one versioned definition computed as of a set date, then reruns and rephrasings agree, because nobody rewrites the formula | Same answer on rerun and rephrasing, request 2: 100% of 20 questions | Fewer pack corrections; unobserved |
| 3 | A manager decision mixes numbers and letters, so issues get missed | Unobserved | If numbers come from the governed layer and issues from cited letters, then every issue appears with its source | Planted letter issues found with a citation, request 3: 100% | Fewer surprises at re-up; unobserved |

**Must not get worse:** wrong numbers presented as sourced. Limit: zero on the 60 questions.

**Supporting evidence:** the brief's three requests and the Calder Packaging journey (`context-library/strategy/brief.md`). No user research exists yet; every "today" value is assumed.

---

## Strategic Fit

Supports goal (A) of the brief, a measured prototype, and goal (B), education on graphs and semantic layers. The finding is a combination: one shared foundation, a different front end per request.

**Impact sizing (assumed, no observed baseline).** An LP with 2 analysts spending 20% of their time on ad hoc questions frees about 0.3 of a full-time role if time per answer falls 80%. Confidence: low. De-risk: timed human run on 10 questions.

**Alternatives considered:** buy a portfolio monitoring product (rejected for the prototype: no access, and it hides the definitions we want to test); documents plus a chatbot only (kept as baseline A, the thing to beat).

---

## Value Equation (Hormozi)

Carried forward from the opportunity analysis. Scope unchanged.

| Factor | This solution |
|---|---|
| **Dream outcome** | "I send the CIO a correct answer with every route and source before 09:00, and it matches last quarter's pack." |
| **Perceived likelihood** | Low at first: chatbots invent numbers. Rises only if every number shows source and as-of date and the tool refuses instead of guessing |
| **Time delay** | Minutes per question once built; weeks to agree definitions and identity links (assumed) |
| **Effort & sacrifice** | Sara asks in plain words. The data team gives up local spreadsheet formulas and owns one definition per metric |

**Verdict:** strong outcome, weak belief. Cheapest lever: show source and as-of on every number, publish the test results.

---

## Non-Goals

- **Real data or real systems.** No access, and the names policy forbids it. Synthetic only.
- **Rebuilding streaming.** Measured in Secondaries Radar: batch won for a weekly decision window. Each source here keeps a schedule and an as-of date instead.
- **Forecasting returns.** The 12-month call forecast is a stated, versioned rule, not a model of manager behaviour.
- **Optional foundation E (graph only).** Built only as a timing comparison for sums at scale, not as a full answerer.
- **Not tackled:** PDF parsing of real layouts (synthetic report text only), people data beyond invented manager partners.

**Trade-offs made:** offline stand-ins replace the AI in every test run, so tests and the demo run with no key; the cost is that offline A and B show what each mechanism can and can't do, not Claude's real error rate.

---

## Annex A, Napkin Sketch

### Screen 1, Ask (Calder Packaging, Monday 08:12)
**JTBD.** When the CIO asks about a company in the news, Sara wants every route and the latest known value, so she can reply before 09:00.
**Primary CTA.** "Copy answer to send".

```
+------------------------------------------------------------+
| Ask a portfolio question          as: Sara (analyst)       |
| [How exposed are we to Calder Packaging?            ] [Ask]|
+------------------------------------------------------------+
| $X.Xm through 4 routes, after the 10 Sep write-down.       |
|  1 Halvane V (fund)          $..m  report 30 Jun, letter   |
|  2 Selbrook FoF III > ...    $..m  report 30 Jun           |
|  3 Co-investment CPG Hold.   $..m  statement 30 Jun        |
|  4 Tellmar III (bought 2024) $..m  report 30 Jun           |
| Definition: look-through exposure v2, owner Risk team      |
| Freshness: holdings 1 day, reports 118 days, letters 46 d  |
| [Copy answer to send]  [Show routes on the graph]          |
+------------------------------------------------------------+
```

### Screen 2, Committee pack (Thursday)
**JTBD.** When the committee meets, Sara wants the 2019 to 2021 buyout funds against plan on last quarter's definitions, so the pack needs no rework.
**Primary CTA.** "Export pack as of 30 Sep 2026".

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

Four foundations share one synthetic world. Each is paired with the front end that suits each request.

| # | Foundation | What the AI does | What code does |
|---|---|---|---|
| A | Documents + search | Reads the top passages and writes the answer | Search over report, letter, notice and news text |
| B | Warehouse tables + AI-written SQL | Writes SQL from the table list | Runs the SQL read-only |
| C | Tables + semantic layer | Picks a governed metric, filters and date from a menu | Compiles the request to SQL, checks access, computes |
| D | C + graph | Same as C, plus routes path and identity questions to the graph | Walks ownership routes and company identity links |

**Front ends:** chat (request 1), governed dashboard with 3 views (request 2), briefing note (request 3), notebook or SQL page for the data team.

**Data:** six synthetic sources, each with its own rhythm and as-of date: holdings (daily), capital calls and distributions (notice text, about weekly), quarterly reports (45 to 90 days late, each manager its own layout and spelling), manager letters (whenever, turned into dated events with a confidence; low confidence waits for a person), company reference data (slow-changing, parents), news (every 15 minutes, never a source of numbers).

**Stack, to decide by measurement** (one decision doc each in `outputs/decisions/`): graph engine (DuckDB recursive SQL, DuckPGQ, NetworkX, archived or server options), semantic layer (own YAML against an established open-source layer), storage layers (bronze, silver, gold in DuckDB), where the AI sits (it picks, code computes).

---

## AI Behavior Contract

| Dimension | Specification |
|---|---|
| **Primary tasks** | Route (which foundation path), extract (question to a metric request), generate (answer text from computed numbers) |
| **Inputs available** | The question, the asker's role, the metric menu (C, D), table list (B), retrieved passages (A) |
| **Constraints** | Every number comes from code or a cited passage. The AI never does arithmetic in text. Synthetic data only |
| **Disallowed** | Numbers from news; numbers with no source; answering a metric with no governed definition; showing data the role can't see; real organisation names |
| **Model** | `claude-sonnet-5-5` when `ANTHROPIC_API_KEY` is set; an offline stand-in otherwise |
| **Latency budget** | p50 under 10 s, p95 under 30 s for one answer, live; offline under 1 s |

**Behavior examples:**

| Scenario | User input | Expected output | Rejection criteria |
|---|---|---|---|
| Happy path | "How exposed are we to Calder Packaging?" | Total, 4 routes, write-down of 10 Sep applied, definition, as-of per number | N/A |
| Spelling | "What do we hold in CPG Holdings?" | Same company, same total, says "CPG Holdings is the holding company of Calder Packaging Ltd" | N/A |
| Follow-up | "And excluding co-investments?" | Total minus the co-investment route, same definition | N/A |
| Point in time | "As of 5 September, how exposed were we to Calder?" | No write-down applied: the letter arrived 10 September | N/A |
| Should refuse, role | Sara asks "What fees do we pay on the CPG co-investment?" | Refusal: her role can't see co-investment fee terms; names who can | Column-level access |
| Should refuse, no definition | "What's our PME against the index?" | Refusal: no governed definition of PME; names the metric owner to ask | No definition in the registry |
| Should refuse, news number | "News says Calder's debt is $400m, what's our share?" | Refuses to use the news figure; offers exposure from governed data | News is never a source of numbers |

**Graceful degradation:** live call fails, then offline stand-in answers and says so; low-confidence letter event, then shown as "waiting for review", not counted.

**Evaluation plan:** 60 questions (20 per request) with known answers from the generator, traps included. Gate in pytest: C and D must answer every non-trap question correctly offline and refuse every refusal trap.

---

## Success Metrics

**Primary:** time until Sara has a correct, sourced answer she would send, including checking time. A wrong answer fails, however fast. Checking time is a stated model (assumed): 20 s to read, 5 s per number shown with source and definition, 120 s per number she must verify by hand. Baseline: hours (assumed). Target: under 10 minutes per question on the winning combination.

**Also measured:** correctness (number within 0.5%, and routes), latency p50 and p95, cost per answer, freshness, correct refusals, same answer on rerun, build effort (moving parts, lines of code), and results at 10 and 100 times the data.

**Guardrail:** zero wrong numbers presented as sourced.

**Kill criteria:** if C or D fails a non-trap question offline, the eval gate blocks the build. If the live run shows the AI picking the wrong metric on more than 5% of questions, the chat front end is removed and the dashboard and briefing note stay.

---

## Rollout Plan

**Approach:** demo first, on Streamlit Community Cloud, no servers.
- **Phase 1:** offline demo and committed eval results. Passing: all tests pass with no key.
- **Phase 2:** live eval with `claude-sonnet-5-5` run locally by the PM (one command). Passing: guardrail holds.
- **Phase 3 (next):** timed human run on 10 questions with one analyst.

**Rollback:** if the live run breaks the guardrail, the demo stays offline-only.

---

## Risks and Recovery

| Risk | Detection | Fallback | Owner |
|---|---|---|---|
| The checking-time model decides the ranking | Sensitivity table: ranking under half and double the per-number times | Report correctness separately from time | PM |
| Offline A and B stand-ins flatter C and D | Live eval differs from offline | Publish live results next to offline; label offline as mechanism test | Engineering |
| Answers known from the same generator the pipeline reads | Truth computed from generator objects in a separate code path | Test that truth code imports nothing from the foundations | Engineering |
| Synthetic letters easier to read than real ones | Not detectable here | State it in Limitations | PM |

---

## Open Questions

- [ ] Can one analyst do a timed run on 10 questions? @PM
- [ ] Which team owns look-through exposure in a real LP: risk or investment? @PM (synthetic owner: Risk team)

---

## Appendix: challenges to the brief (written down, as the brief asks)

1. **The main metric depends on an assumed checking-time model.** A foundation that shows sources wins partly by construction. We publish a sensitivity table and report correctness on its own.
2. **Offline A and B are deterministic stand-ins for an AI.** They show each mechanism's limits, not Claude's error rate. Live results are a separate, labelled run.
3. **"Graph for company identity" mixes two jobs.** Identity matching is a lookup problem an alias table can also solve. We test C plus an alias table, so the graph has to earn its place on routes, not only spellings.
4. **20 questions per request is small.** One question moves a score by 5 points. We report counts, not only shares.
5. **The forecast and plan figures are rules, not truth.** For the call forecast, "correct" means "matches the governed rule as of the date", which tests consistency, not foresight.

**Name check.** Options: "Portfolio Answer Desk" (answers leaders' portfolio questions, with sources), "Look-Through Finder" (too narrow: only exposure), "LP Question Bench" (names the test, not the job). Picked: **Portfolio Answer Desk**. The test bench inside is called "Foundation test".
