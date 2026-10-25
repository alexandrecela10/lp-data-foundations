# Brief: which data foundation gets Sara the right answer fastest?

Agreed with the PM on 2026-10-25. Challenge it where it's weak, and write the challenge down.

## Goal

Study four data foundations, each paired with the interface that suits it, and find the one that lets one analyst answer requests from senior leaders **correctly and fastest**. Make the reader understand graph databases, semantic layers and internal data analysis at scale, with plain English and pictures. Two goals, equal weight: (A) a working, measured prototype; (B) education anyone can follow.

## Persona

**Sara, a portfolio analyst in the private equity team of a large LP** (an investor that commits money to many private equity funds). The CIO's office and the investment committee send her ad hoc questions. Today each takes her from hours to a day: she searches fund reports and spreadsheets by hand.

## Three requests, three askers

| | Request 1: an event | Request 2: a regular pack | Request 3: a relationship decision |
|---|---|---|---|
| Who asks | The CIO, Monday 08:12 | The investment committee, for Thursday's meeting | The head of private equity, deciding whether to invest in a manager's next fund |
| The question | "How exposed are we to Calder Packaging, and to European packaging? Through which managers? Did we know it was in trouble?" | "How are our 2019 to 2021 buyout funds doing against plan, after fees? How much of our unfunded commitment will be called in the next 12 months?" | "Manager X is raising Fund VI. What's our history with them: commitments, results fund by fund, co-investments, and any issues raised in their letters?" |
| What matters most | Speed and completeness: every path, latest news | Consistency: same definitions as last quarter's pack, as of a set date | Numbers plus what letters said, with sources |
| Why it's hard | The company sits behind several hops (fund of funds, fund, co-investment, a stake bought second-hand) and under three spellings; the write-down is only in a manager letter | Net IRR, TVPI, DPI, unfunded and the 12-month call forecast must be defined once and computed as of a date | Mixes tables, free text and links between people, funds and deals |
| Guess at the winner | Graph for paths and company identity, plus events read from letters | Semantic layer; the graph adds nothing | Hybrid: semantic layer for numbers, search over letters with citations, graph for links |
| Likely best interface | Chatbot | Governed report or dashboard | Generated briefing note with sources |

### Request 1 journey (input, processing, output)
1. **08:10 input.** News: Calder Packaging is restructuring its debt.
2. **08:12 question** from the CIO (above).
3. **Processing:** understand the question (metric look-through exposure, filters, as-of date) → resolve the company ("Calder Packaging Ltd", "Calder Pack.", "CPG Holdings") → find every path → compute with governed definitions (our share of the fund × the company's share of the fund's value, at the latest report, adjusted for events learnt since, counting only what we knew by then) → check access (Sara sees exposure, not co-investment fee terms).
4. **08:20 output:** one paragraph (total, paths, the write-down and when we learnt of it, the sector total), the paths, every definition, the as-of date of every number, the freshness of each source.

## Data (all synthetic, generated with known answers)

Extend the synthetic world of github.com/alexandrecela10/secondaries-radar (funds, managers, our holdings, fund events) with portfolio companies (with name variants and parent companies), funds of funds, co-investments, stakes bought second-hand, people (manager partners), and letters.

| Source | Arrives | Structure | Difficulty |
|---|---|---|---|
| Our holdings and commitments (accounting system) | Daily | Structured | Point in time |
| Capital calls and distributions | When they happen, about weekly | Semi-structured (email + PDF text) | Read into fixed fields |
| Fund quarterly reports and lists of companies held | Quarterly, 45 to 90 days late | Semi-structured; each manager has its own layout | Read tables; spelling varies |
| Manager letters (exits, write-downs, team changes, issues) | Whenever | Free text | Turn into dated events with confidence; low confidence waits for a person |
| Company reference data (sector, country, parent) | Slow-changing | Structured | History; subsidiaries linked to parents |
| Public-style news (synthetic) | Every 15 minutes | Free text | Triggers questions; never a source of numbers |

Each source has a schedule and an as-of date. Answers show how fresh each part is. Don't rebuild streaming (already measured in Secondaries Radar); reuse that result.

## Foundations compared

| # | Foundation | Tests |
|---|---|---|
| A | Documents + chatbot with search (no structured data) | The "just give the AI our files" baseline |
| B | Warehouse tables + the AI writes SQL | The common approach; multi-hop questions and inconsistent definitions |
| C | Tables + semantic layer; the AI only picks from governed metrics and dimensions | Consistency and refusals |
| D | C + a graph for ownership paths and company identity; the AI routes paths to the graph and numbers to the semantic layer | Whether the graph earns its place |

Optional E only if time allows: graph only, to show graphs are poor at sums.

**Interfaces:** chatbot, governed dashboard (3 views), analyst notebook or SQL, a generated briefing note. Each foundation is run with the interface that suits each request; the result is a winning combination, not one tool.

**Stack to decide in the PRD, measured, not assumed.** Verify the current status and licence of each candidate before choosing (some projects have changed or been archived):
- graph: a property graph on DuckDB (an SQL/PGQ extension), an embedded graph database, a server graph database (Neo4j, local only if it can run), NetworkX for teaching;
- semantic layer: a small YAML metric layer of our own, against an established open-source one.

The demo must run on Streamlit Community Cloud: no servers.

## Test set and metrics

- **60 questions:** 20 versions of each request. They include rephrasings, follow-ups ("and excluding co-investments?") and traps: a company under three spellings, a question Sara's role can't see, a metric with no definition, a date before a letter arrived. Every answer is known from the generator.
- **Main metric: time until Sara has a correct, sourced answer she would send,** including her checking time. A wrong answer fails, however fast. Checking time is a stated model, for example a few seconds per number shown with its source and minutes per number she must verify by hand. Document it as an assumption; a timed human run on 10 questions is "next".
- **Also:** correctness (number within tolerance, and path), time to answer (median and 95th percentile), cost per answer, freshness, correct refusals, the same answer on a rerun, build effort (moving parts, lines of code).
- **Scale:** rerun at 10 and 100 times the data size, to show where the graph starts or stops paying off.

**Expected answer, to prove or break:** one shared foundation (semantic layer + graph used only for paths and identity) with a different front end per request. If C gets within a few minutes of D on request 1, say the graph isn't worth it at this size.

## Governance (the data leader's view)

Roles and access (row and column level); every metric with an owner, a definition, a version and tests; point in time; lineage on every number; data contracts between layers, with bad rows blocked and logged; an audit log of every question, answer and definition used; refusal when no governed definition exists or access is denied; no personal data beyond invented manager partners.

## Engineering (the engineering lead's view)

Layers (bronze, silver, gold), typed contracts, deterministic generator with a seed, pure tested functions for every metric, an eval gate in pytest, one command to rebuild everything, tracing of each answer (inputs, outputs, time, cost), and a decision doc per architecture choice with the measured trade-off.

## Education (very visual)

Follow the `/prototype` demo blueprint. In addition:
- **Show the graph working:** an interactive picture of the Calder Packaging paths (our LP → fund of funds → fund → company; co-investment; the stake bought second-hand), with each hop highlighted as the query walks it. Then the same question as SQL with joins, as a graph query and as a semantic-layer request, side by side.
- **Explain the semantic layer** with one metric (look-through exposure): its definition, its owner, and the same number in the dashboard, the notebook and the chatbot. Then a counterfactual: two teams with two definitions get two different answers.
- **Chatbot vs other ways in:** where each wins, on the 60 questions.
- **At scale:** what changes at 10 and 100 times the data, with a chart.
- **A "choices behind it" section:** each choice, the options, what we picked, why, what we gave up, one picture each.
- Plain English for someone outside finance and engineering; every concept with one example and its counterfactual.

## Opportunity analysis: include commercial value

Beyond the time saved for one LP, size who would pay for this foundation and why:
- large LPs and their data teams;
- fund administrators;
- portfolio monitoring software vendors (as categories);
- consultants.

Cover build against buy. Use public, cited numbers where possible; mark everything else assumed.

## Definition of done

1. Opportunity analysis (Go/No-go), PRD reviewed with blockers fixed, journey map, decision docs.
2. A working build: generator, six sources, foundations A to D, interfaces, 60-question eval with results committed, scale runs, all tests passing with no keys.
3. A Streamlit demo following the blueprint, with the visual education above.
4. Case study draft in `outputs/portfolio/<slug>/` (`index.html`, `linkedin.md`, `name-audit.md`, goals and state files) following `/portfolio-case-study`; hero numbers prove value.
5. A short final report in the PR: what was measured, what won, what's assumed, what the PM must decide.
