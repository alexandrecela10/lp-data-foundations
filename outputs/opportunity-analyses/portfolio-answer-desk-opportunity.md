# Portfolio Answer Desk: Opportunity Analysis

**Date:** 2026-10-25 (revised the same day: vision added, commercial value shortened and sized)
**Owner:** PM (drafted by Claude, run unattended with PM approval)
**Status:** Go

## Vision

**A senior leader at a large investor asks a question about the portfolio and gets a correct answer, with its sources, in minutes. Two analysts asked the same question give the same number.**

This project moves toward that in two ways:
- **Proof.** It measures which way of organising the data gets an analyst to a correct, sourced answer fastest, on 60 questions with known answers.
- **Teaching.** It explains the building blocks behind it in plain words, so a data leader can pick them knowingly.

## Problem Statement

Senior leaders at a large LP ask unplanned questions about the portfolio. An LP is an investor, such as a pension fund, that commits money to many private equity funds. Each answer takes an analyst hours to a day. Two analysts can return two different numbers for the same question.

## Current Situation

Sara, a portfolio analyst, answers by hand. She searches fund reports, manager letters and spreadsheets, then adds up what she finds.

**A concrete case (hypothetical, synthetic data).** Monday 08:10, the news says Calder Packaging is restructuring its debt. At 08:12 the CIO asks: "How exposed are we, through which managers, and did we know?"
- We hold the company through four routes: a fund we invested in, a fund that invests in other funds, a direct investment alongside a manager (a co-investment), and a fund stake we bought from another investor.
- The company appears under three spellings across those reports.
- A drop in its value appears only in a manager letter dated 10 September.

Sara finds the first route in minutes. The other three routes and the letter take the rest of the morning, and she may still miss one. Had the company sat in one fund under one name, she'd have answered in five minutes.

## Proposed Solution

**One shared, organised set of portfolio data, with a different screen for each of the three kinds of request:**

- **The CIO's question about a company in the news:** a chat assistant. An AI reads the question and picks which agreed calculation to run. Code does the maths. Every number shows its source and the date it was true.
- **The investment committee pack:** a dashboard where each measure (for example a fund's return) has one written definition, one owner and a version number, computed as of a set date.
- **A decision on whether to invest in a manager's next fund:** a briefing note with the numbers, plus what the manager's letters said, each line citing its letter.

Code checks the AI's work. The AI can only pick calculations that exist. It refuses when no agreed definition exists, or when the person asking isn't allowed to see the data.

## Problems, hypotheses and success

| # | Problem | Today | Hypothesis | Success metric (target) | Expected impact |
|---|---|---|---|---|---|
| 1 | A question about a company takes hours, because the company hides behind several routes and spellings | Unobserved (the brief says hours to a day; never timed) | If routes and spellings are linked once in the data, then every route is found in seconds, because code follows the links instead of a person searching | Time to a correct, sourced answer Sara would send: under 10 minutes, on 20 test questions | Leaders get the answer before their 09:00 meeting; unobserved until a timed test with analysts |
| 2 | The committee pack changes from quarter to quarter, because each analyst computes returns and expected cash calls their own way | Unobserved | If each measure has one written, versioned definition computed as of a set date, then reruns and reworded questions give the same number, because nobody rewrites the formula | Same answer on a rerun and a rewording: 100% of 20 test questions | Fewer corrections to the pack; unobserved |
| 3 | A decision on a manager mixes numbers and letters, so problems get missed | Unobserved | If numbers come from the agreed definitions and problems from cited letters, then every known problem shows up with its source, because search covers every letter | Known letter problems found with a citation: 100% | Fewer surprises at the decision; unobserved |

**Must not get worse:** wrong answers sent. Target: zero wrong numbers shown with a source, on the 60 test questions.

**Not tackled here:** live data from real systems (no access; synthetic data only); forecasting returns (out of scope; the 12-month cash call forecast uses a stated rule).

## Commercial value

**Who would pay, and why.** Links are public sources; everything else is assumed.

| Buyer | Why they'd pay | Evidence |
|---|---|---|
| Large LPs and their data teams | Faster answers to leaders, one number per question | Half of LPs plan to put more money into private equity in the next 12 months ([Preqin 2025](https://www.preqin.com/insights/global-reports/2025-private-equity)). More funds means more routes to trace |
| Fund administrators (firms that keep a fund's books) | Sell on-demand answers to their LP clients | 64% of LPs expected on-demand or daily performance reporting to become normal within three years ([CSC 2023 via Real Deals](https://realdeals.eu.com/article/ad-hoc-portfolio-reporting-to-be-expected-in-the-next-three-years)) |
| Portfolio monitoring software vendors (as a category) | Add agreed definitions and route-following to their product | A standard reporting template applies from Q1 2026 ([ILPA](https://ilpa.org/wp-content/uploads/2025/09/Combined-Overview-ILPA-Templates.pdf)); standard fields make shared definitions easier to sell |
| Consultants | Sell the setup (definitions, company matching, access rules) as a project | Assumed: 3 to 6 months per LP |

**Build against buy.** The software parts are open source and small. The costly work is agreeing definitions, matching company names and setting access rules, and no vendor ships those filled in.

**Rough value for one large LP (all assumed).** Value = cases a year × hours per case today × share of time saved × value per hour.

| Request | Cases a year | Hours per case today | Time saved | Value per hour | Value a year |
|---|---|---|---|---|---|
| 1. CIO's question about a company | 100 (about 2 a week) | 4 | 80% | $100 (analyst cost) | $32,000 |
| 2. Committee pack | 4 packs | 26 (20 to build, 6 to correct) | about 60% (half the build, all the corrections) | $100 | $6,400 |
| 3. Decision on a manager's next fund | 12 | 8 | 50% | $100 | $4,800 |
| **Total** | | | | | **about $43,000, or a quarter of one analyst** |

- **Across the market:** about $13m a year if 300 LPs worldwide have a team answering these questions (assumed; counting them is a discovery task).
- **The larger value isn't priced:** a leader decides on the full exposure, not 1 of 4 routes. Time saved alone wouldn't justify agreeing definitions across teams.
- **What would change the estimate most:** hours per case today. The timed test with former LP analysts measures it.

## Value Equation (Hormozi)

> Value = (Dream Outcome × Perceived Likelihood of Achievement) / (Time Delay × Effort & Sacrifice), from Alex Hormozi's *$100M Offers*. Internal tool: read "would they use it".

| Factor | This solution |
|---|---|
| **Dream outcome** | Sara: "I send the CIO a correct answer with every route and source before 09:00, and it matches last quarter's pack." |
| **Perceived likelihood** | Low at first. Analysts have seen chatbots invent numbers. Belief rises only if every number shows its source and date, and the tool refuses instead of guessing |
| **Time delay** | Minutes per question once the data is organised. Organising it (definitions, company links) takes weeks, assumed |
| **Effort & sacrifice** | Sara changes little: she asks in plain words. The data team must agree one definition per measure and own it, and give up their local spreadsheets |

**Verdict.** Strong outcome, weak belief. The cheapest lever is belief: show the source and date on every number, and publish how often it's right on a test with known answers.

## Recommendation

**Go.** The pain is concrete. The test can prove or break the claim with known answers. The build uses open-source parts and needs no servers. Next: `/prd-draft`.

Sources: `context-library/strategy/brief.md`; links inline above.
