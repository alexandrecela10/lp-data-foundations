# Portfolio Answer Desk: Opportunity Analysis

**Date:** 2026-10-25
**Owner:** PM (drafted by Claude, run unattended with PM approval)
**Status:** Go

## Problem Statement

Senior leaders at a large LP (an investor that commits money to many private equity funds) ask ad hoc portfolio questions. Each answer takes an analyst hours to a day, and two analysts can return two different numbers for the same question.

## Current Situation

Sara, a portfolio analyst, answers by hand. She searches fund reports, manager letters and spreadsheets, then adds up what she finds.

**A concrete case (labelled hypothetical, synthetic data).** Monday 08:10, news says Calder Packaging is restructuring its debt. At 08:12 the CIO asks: "How exposed are we, through which managers, and did we know?" The company sits behind four routes: a fund we committed to, a fund of funds, a co-investment and a fund stake bought second-hand. It appears under three spellings. The write-down sits only in a manager letter from 10 September. Sara finds the direct fund in minutes. Finding the other three routes and the letter takes the rest of the morning, and she may still miss one.

## Proposed Solution

One shared data foundation that answers three kinds of request, each through the front end that suits it:

- **For the CIO's event question:** a chat assistant. A language model (an AI that reads and writes text) turns the question into a request for governed numbers; code computes them; every number shows its source and as-of date.
- **For the investment committee pack:** a governed dashboard where each metric has one definition, an owner and a version, computed as of a set date.
- **For a manager decision:** a generated briefing note: the numbers, plus what the manager's letters said, each line cited.

Code checks the AI's work: it can only pick metrics that exist, and it refuses when no definition exists or the asker's role can't see the data.

## Problems, hypotheses and success

| # | Problem | Today | Hypothesis | Success metric | Expected impact |
|---|---|---|---|---|---|
| 1 | An event question takes hours because the company hides behind several routes and spellings | Hours (assumed, from the brief; not timed) | If routes and company spellings are linked once in the data, then every route is found in seconds, because the walk is done by code, not by search | Time to a correct, sourced answer Sara would send, request 1: under 10 minutes on 20 test questions | Leaders get an answer before their 09:00 meeting; unobserved until a timed human run |
| 2 | The committee pack drifts because each analyst computes IRR, TVPI and calls their own way | Unobserved | If each metric has one versioned definition computed as of a set date, then reruns and rephrasings return the same number, because no one rewrites the formula | Same answer on rerun and rephrasing, request 2: 100% of 20 test questions | Fewer pack corrections; unobserved |
| 3 | A manager decision mixes numbers and letters, so issues get missed | Unobserved | If numbers come from the governed layer and issues from cited letters, then every issue is shown with its source, because search covers every letter | Share of known issues found with a citation, request 3: 100% of planted issues | Fewer surprises at the re-up decision; unobserved |

**Must not get worse:** wrong answers sent. Target: zero wrong numbers presented as sourced on the 60-question test set.

**Not tackled here:** live data feeds from real systems (no access; synthetic only); forecasting returns (out of scope; the 12-month call forecast uses a stated rule).

## Commercial value

Who would pay for this foundation, and why. Numbers are public where cited; everything else is assumed.

| Buyer | Why they'd pay | Build or buy today | Evidence |
|---|---|---|---|
| Large LPs and their data teams | Faster, consistent answers to leaders; one definition per metric | Mostly build on a warehouse plus spreadsheets; buy point tools | Half of LPs plan to raise private equity allocations in the next 12 months ([Preqin 2025](https://www.preqin.com/insights/global-reports/2025-private-equity)). More funds per LP means more routes to trace |
| Fund administrators | Sell look-through and on-demand answers as a service to LP clients | Build on their own data platforms | 64% of LPs expected on-demand or daily performance reporting to become normal within three years ([CSC 2023 via Real Deals](https://realdeals.eu.com/article/ad-hoc-portfolio-reporting-to-be-expected-in-the-next-three-years)) |
| Portfolio monitoring software vendors (as a category) | Add a governed metric layer and a path graph to their product | Build | The ILPA reporting template update applies from Q1 2026 and the performance template from Q1 2027 ([ILPA](https://ilpa.org/wp-content/uploads/2025/09/Combined-Overview-ILPA-Templates.pdf)). Standard fields make a shared metric layer easier to sell |
| Consultants | Deliver the setup (definitions, identity matching, governance) as a project | Bill time | Assumed: a 3 to 6 month setup project per LP |

**Build against buy.** The engine pieces are open source and small: DuckDB, a YAML metric layer, a graph library. The work that costs money is definitions, company identity and governance, which a vendor can't ship pre-filled. **Assumed:** an LP with 2 analysts spending 20% of their time on ad hoc questions frees about 0.3 of a full-time role (2 × 20% × 80%) if the time per answer falls by 80% or more.

## Value Equation (Hormozi)

> Value = (Dream Outcome × Perceived Likelihood of Achievement) / (Time Delay × Effort & Sacrifice), from Alex Hormozi's *$100M Offers*. Internal tool: read "would they use it".

| Factor | This solution |
|---|---|
| **Dream outcome** | Sara: "I send the CIO a correct answer with every route and source before 09:00, and it matches last quarter's pack." |
| **Perceived likelihood** | Low at first. Analysts have seen chatbots invent numbers. Belief rises only if every number shows its source and as-of date, and the tool refuses instead of guessing |
| **Time delay** | Minutes per question once the foundation exists. Building the foundation (definitions, identity links) takes weeks, assumed |
| **Effort & sacrifice** | Sara changes little: she asks in plain words. The data team must agree one definition per metric and own it. That's the real sacrifice: giving up local spreadsheets |

**Verdict.** Strong outcome, weak belief. The cheapest lever is belief: show the source and as-of date on every number, and measure correctness on a public test set before anyone relies on it.

## Recommendation

**Go.** The pain is concrete, the test set can prove or break the claim with known answers, and the build uses open-source parts that run with no servers. Next: `/prd-draft`.

Sources: `context-library/strategy/brief.md`; links inline above.
