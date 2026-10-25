# Portfolio Answer Desk

**A portfolio question desk for the private equity team of a large LP.** An analyst types a senior leader's question ("How exposed are we to Calder Packaging, and through which managers?") and gets an answer she can send: the number, every route behind it, the definition used, and the date and source of every figure. Inside sits a test bench that runs 60 questions through five data setups and measures which one gets her to a correct, sourced answer fastest.

Synthetic data. Not investment advice. All names are invented.

## The five setups tested

The same 60 questions, 20 for each of three requests, go through five ways of organising the data. Every right answer is known, because the data is generated.

| Setup | How the data is organised | What the AI does | What code does |
|---|---|---|---|
| A | Documents plus search | Reads the passages and writes the answer | Searches the text |
| B | Warehouse tables | Writes the SQL query | Runs it, read-only |
| C | Tables plus a semantic layer (a list of agreed calculations) | Picks a calculation, filters and a date | Turns the pick into SQL and computes |
| C+ids | C plus an identity table (which names are the same company) | Same as C | Same as C, and treats every spelling as one company |
| D | C+ids plus a graph and letter search | Same as C | Also follows ownership and people links, and searches letters |

## What we found, offline and live

**Offline:** fixed rules stand in for the AI (`evals/results/offline-seed42.json`). **Live:** `claude-sonnet-5-5` reads every question for every setup, reads the passages in A and writes the SQL in B (`evals/results/live-claude-sonnet-5-5.json`; 2 passes, 960 calls, 0 failed calls, $6.25 billed, 47 minutes).

| Setup | Correct of 60, offline / live | CIO event (of 20) | Committee pack (of 20) | Manager decision (of 20) | Wrong numbers shown with a source | Same answer on a rerun, live | Expected time per question* |
|---|---|---|---|---|---|---|---|
| A documents + search | 18 / 7 | 4 / 2 | 4 / 2 | 10 / 3 | 27 / 7 | 90% | 84 / 106 min |
| B tables + AI-written SQL | 22 / 11 | 3 / 2 | 6 / 3 | 13 / 6 | 0 / 0 | 80% | 77 / 98 min |
| C tables + semantic layer | 41 / 41 | 5 / 5 | 20 / 20 | 16 / 16 | 15 / 15 | 100% | 38 / 38 min |
| C+ids: C + identity table | 56 / 56 | 20 / 20 | 20 / 20 | 16 / 16 | 2 / 2 | 100% | 8.6 / 8.6 min |
| D: C+ids + graph + letter search | 60 / 60 | 20 / 20 | 20 / 20 | 20 / 20 | 0 / 0 | 100% | 0.7 / 0.6 min |

\*Answer time plus Sara's checking time under a stated, assumed model, with a wrong answer costing 2 hours of manual work (assumed).

**What this test showed**
- **C, C+ids and D scored the same live as offline,** on every question. In these three setups Claude fills in the question's fields and code computes the number.
- **A fell from 18 to 7 and B from 22 to 11 live.** Many of A's live answers were withheld by the number checker, because they contained numbers not in the passages. On reworded questions, A and B gave the same answer 50% of the time.
- **What broke C on the CIO's question was spelling.** Calder Packaging appears as "Calder Pack." and "Calderwick Holdings" in 3 of its 5 routes. The identity table fixed all 15 of C's misses on that request; the fund-of-funds hop was not the problem.
- **The graph tied C+ids on routes** (20 of 20 each, offline and live). D's 4 extra correct answers are manager questions: 2 on people links, 2 on a letter. B, with SQL on the people table, also answered both people-link questions.
- **A first live attempt was invalid.** The question schema had 18 nullable fields and the API allows 16, so every live read fell back to the offline reader without saying so. Any failed live call now marks the run invalid.

**Decision.** C+ids for numbers and routes, the graph for people links, letter search for manager history, and a different front end per request: chat for the CIO's event, a dashboard for the committee pack, a briefing note for a manager decision. By the rule set before the run, the graph had to beat C+ids by 2 questions or 2 minutes on the CIO's request; it tied. **Open:** C+ids shows 2 wrong numbers with a source, and the guardrail is zero.

**At 10x and 100x the data** (`evals/results/scale.json`): one company's routes stay under a second every way (recursive SQL 538 ms, graph build plus walk 735 ms, DuckPGQ query 25 ms at 100x). What slowed down was our own code: a governed metric computed one fund at a time (9.3 s) and company-name matching (68 s of a 99 s rebuild).

**What is assumed.** The checking-time model is an assumption until a timed test with analysts. If Sara rechecks half the sourced numbers by hand, the time advantage disappears; the correctness counts don't change. The data, the companies and the letters are synthetic.

**Learn how it works.** The demo's "How the foundations work" tab (also `static/foundations.html`) animates the Calder question through each setup: where each finds the routes, where it goes wrong, and what each building block changes.

## Run it

```
pip install -e ".[app,dev]"
pytest                                           # no key needed
streamlit run app.py
PYTHONPATH=src python -m answerdesk.cli all      # rebuild everything: data, evaluations, scale runs
ANTHROPIC_API_KEY=... PYTHONPATH=src python -m answerdesk.cli live   # live evaluation (about $6, 47 min)
PYTHONPATH=src python -m answerdesk.cli explainer  # rebuild static/foundations.html
```

The hosted demo on Streamlit Community Cloud runs offline with no key and no server (`app.py`, `requirements.txt`, Python 3.11).

## Where things are

- `context-library/strategy/brief.md`: the brief.
- `outputs/`: opportunity analysis (Go), PRD with the seven-reviewer synthesis, journey map, decision docs, case study draft.
- `docs/`: `DEFINITIONS.md` (written before the code), `ARCHITECTURE.md` (with a licence table), `GLOSSARY.md`.
- `src/answerdesk/`: generator, six sources, pipeline, semantic layer, graph, the five setups, evaluation, scale.
- `evals/results/`: committed results (offline, held-out world, scale, live).
- `static/foundations.html`: the animated explainer, built from those results.

Built with PM OS. Patterns reused from [Secondaries Radar](https://github.com/alexandrecela10/secondaries-radar).
