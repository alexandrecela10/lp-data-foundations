# Portfolio Answer Desk

**A portfolio question desk for the private equity team of a large LP.** An analyst types a senior leader's question ("How exposed are we to Calder Packaging, and through which managers?") and gets an answer she can send: the number, every route behind it, the definition used, and the date and source of every figure. Inside sits a test bench that runs 60 questions through five data setups and measures which one gets her to a correct, sourced answer fastest.

Synthetic data. Not investment advice. All names are invented.

## What we found (offline mechanism test, 60 questions with known answers)

| Setup | Correct of 60 | CIO event (of 20) | Committee pack (of 20) | Manager decision (of 20) | Wrong numbers shown as sourced | Expected time per question* |
|---|---|---|---|---|---|---|
| A documents + chatbot search | 18 | 4 | 4 | 10 | 27 | 84 min |
| B tables + AI-written SQL | 22 | 3 | 6 | 13 | 0 | 77 min |
| C tables + semantic layer | 41 | 5 | 20 | 16 | 15 | 38 min |
| C+ids: C + identity table | 56 | 20 | 20 | 16 | 2 | 8.6 min |
| D: C + graph (+ letter search) | 60 | 20 | 20 | 20 | 0 | 0.7 min |

\*Answer time plus Sara's checking time under a stated, assumed model, with a wrong answer costing 2 hours of manual work (assumed). Source: `evals/results/offline-seed42.json`.

**Decision.** One shared foundation (tables, a semantic layer, an identity table) with a different front end per request: chat for the CIO's event, a governed dashboard for the committee pack, a briefing note for a manager decision. The graph earns its place only for links between people and managers. On the CIO's request C+ids and D tie at 20/20, so by the rule set before the run the graph doesn't earn its place for routes at this size. The spelling problem, not the hops, was what broke C.

**What is assumed or not yet run.** The AI is replaced offline by fixed readers, so these numbers show what each setup can and can't do, not Claude's error rate. The live run with `claude-sonnet-5-5` is **not yet run** (no key in the build environment). The checking-time model is an assumption; if Sara rechecks half the sourced numbers by hand, the time advantage disappears while the correctness advantage stays.

## Run it

```
pip install -e ".[app,dev]"
pytest                                           # no key needed
streamlit run app.py
PYTHONPATH=src python -m answerdesk.cli all      # rebuild everything: data, evaluations, scale runs
ANTHROPIC_API_KEY=... PYTHONPATH=src python -m answerdesk.cli live   # live evaluation (costs money)
```

The hosted demo on Streamlit Community Cloud runs offline with no key and no server (`app.py`, `requirements.txt`, Python 3.11).

## Where things are

- `context-library/strategy/brief.md`: the brief.
- `outputs/`: opportunity analysis (Go), PRD with the seven-reviewer synthesis, journey map, decision docs, case study draft.
- `docs/`: `DEFINITIONS.md` (written before the code), `ARCHITECTURE.md` (with a licence table), `GLOSSARY.md`.
- `src/answerdesk/`: generator, six sources, pipeline, semantic layer, graph, the five setups, evaluation, scale.
- `evals/results/`: committed results (offline, held-out world, scale; live marked "not yet run").

Built with PM OS. Patterns reused from [Secondaries Radar](https://github.com/alexandrecela10/secondaries-radar).
