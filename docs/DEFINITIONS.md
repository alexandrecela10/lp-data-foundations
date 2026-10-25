# Definitions (written before the semantic layer and the truth code)

Both `src/answerdesk/truth.py` (known answers, from generator objects) and `src/answerdesk/semantic/metrics.yaml` (governed layer, from tables) implement these words. Neither imports the other. A test checks that `truth.py` imports nothing from the foundations.

**Units.** US dollars, millions ("$m"). No currency conversion: every synthetic fund reports in US dollars.

**As of D.** A fact counts on date D only if it happened on or before D **and** we learnt it on or before D. Every row carries both dates: `effective_date` (when it happened, or the report's as-of date) and `learnt_date` (when the document reached us).

> Example: Halvane wrote Calder Packaging down on 2 September 2026; its letter reached us on 10 September. As of 9 September the write-down does not count. As of 10 September it does.

## Metrics

| Metric | Version | Owner | Definition in one plain sentence |
|---|---|---|---|
| `lookthrough_exposure` | v2 | Risk team | Our share of a company's latest reported value, through every route we hold it, adjusted for write-downs and exits we learnt of since that report |
| `lookthrough_exposure` | v1 (retired, kept for the counterfactual) | Investment team | Our commitment to each fund that holds the company, times the company's share of that fund |
| `adjusted_nav` | v1 | Finance | Our latest reported value in a fund, plus calls we paid since that report, minus distributions we received since |
| `paid_in` | v1 | Finance | Capital calls we paid, plus the price we paid for stakes bought second-hand |
| `distributions` | v1 | Finance | Cash the fund paid us |
| `net_tvpi` | v1 | Finance | (Distributions + adjusted NAV) divided by paid-in, from our own cash flows, after all fees |
| `net_dpi` | v1 | Finance | Distributions divided by paid-in |
| `net_irr` | v1 | Finance | The annual return that makes our dated cash flows plus today's adjusted NAV net to zero |
| `unfunded` | v2 (from 1 Aug 2026) | Finance | Commitment, minus calls paid, plus distributions the fund may call back (recallable) |
| `unfunded` | v1 (last used in the Q2 pack) | Finance | Commitment minus calls paid |
| `calls_next_12m` | v2 | Treasury | Unfunded times a rate set by fund age: under 2 years 35%, 2 to 4 years 25%, 4 to 6 years 12%, 6 years or more 5% |
| `tvpi_vs_plan` | v1 | Investment team | Net TVPI minus the plan TVPI for the fund's age; plan stays at 1.0x for 2 years, then rises in a straight line to the target at year 10 |
| `manager_issues` | v1 | Investment team | Every letter from the manager that raises an issue (extension, restatement, key person or team change, fees, incident, write-down), learnt on or before D |

## Rules the metrics share

1. **Route.** A chain of holdings from the LP to a company: LP to fund, LP to fund of funds to fund, LP to a co-investment, LP to a fund stake bought second-hand. Depth limit 5; a holding already on the route is never visited again.
2. **Share of a vehicle.** Our capital account value divided by the vehicle's value, as stated in the vehicle's report. A fund of funds' share of an underlying fund is stated in the fund of funds' report.
3. **Holding company.** Holdings recorded under a holding company whose only asset is one operating company count as that company. Example: Calderwick Holdings holds only Calder Packaging Ltd, so a stake recorded as "Calderwick Holdings" counts as Calder Packaging.
4. **Events.** A write-down multiplies the holding's value by its factor; an exit removes the holding (the money becomes a distribution). Either applies to the holding named in the letter, from its effective date, if we learnt it by D. A manager's letter about its own valuation does not change another manager's valuation of the same company.
5. **Which report.** For each fund, the latest quarter we had by D, from the manager's own report or a fund of funds' copy of it. Same quarter: the manager's own report wins.
6. **No double counting.** The same report row arriving twice (a manager's own report and a fund of funds' copy) counts once; the manager's own report wins. Two different routes to the same company are two different economic interests and both count.
7. **Scope "our funds".** Funds we hold directly, bought new or second-hand. Funds of funds count as one fund each; their underlying funds are not "our funds".
8. **Pooled ratios.** Sums over funds first, then divide.
9. **Low-confidence events.** A letter event read with confidence below 0.8 waits for a person. It never changes a number. Answers say how many such items they left out.
10. **News.** Never a source of numbers.
11. **IRR.** Solved by bisection between -99% and +1,000% a year. If the cash flows never change sign, the answer is "not meaningful".

## Access

| Role | Sees | Doesn't see |
|---|---|---|
| analyst (Sara) | Everything below except the two exclusions | Co-investment fee terms (columns); planned commitments not yet approved (rows) |
| head_of_pe | Everything | |
| cio | Everything except planned commitments not yet approved | Planned commitments (rows) |

**Default dates.** Exposure, letters and people default to today (26 October 2026). Performance metrics default to the last quarter end (30 September 2026), unless the question gives a date or says "today".
