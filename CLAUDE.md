# CLAUDE: lp-data-foundations

**Product (working name, rename in the PRD):** a test bench that finds which data foundation lets an analyst at a large LP answer requests from senior leaders correctly, fastest. It compares four foundations (documents + search, tables + AI-written SQL, tables + semantic layer, semantic layer + graph) on three real kinds of request. It ships with plain-English, visual education on graph databases, semantic layers and internal data analysis at scale.

**Read `context-library/strategy/brief.md` first, every session.** It holds the persona, the three requests, the data sources, the foundations, the metrics and the definition of done.

## PM OS

- `{pm-os}` = `.claude/pm-os/` in this repo (a copy of the PM's operating system). Follow every rule in `.claude/pm-os/CLAUDE.md`: voice, minimal factual, precise enough to need no thinking, decision first, one example and its counterfactual, no em dashes ever, banned words.
- Skills are in `.claude/skills/`. Where a skill says `{pm-os}/templates`, `{pm-os}/sub-agents` or `outputs/portfolio/plain-language-rules.md`, use `.claude/pm-os/templates`, `.claude/pm-os/sub-agents` and `.claude/pm-os/portfolio/plain-language-rules.md`.
- Write PM documents to `outputs/`. `context-library/` holds the brief; do not edit it.

## Hard constraints

- **Names policy.** All data is synthetic, with invented names: the LP, its funds, managers, companies, people and letters. Public sources may be named and linked (for example a public pension's disclosures cited as background). Never name the PM's employer, clients or prospects. Never name or guess any real organisation as "the LP" in this project. Never write the name of a real investor next to a synthetic fact.
- **No keys in the repo.** `.env` is git-ignored. Never print a key.
- **No real fees, terms or holdings** of any real organisation.
- **Disclaimer** on every user-facing surface: "Synthetic data. Not investment advice."

## Working style in the cloud

The PM is away. Work autonomously through the whole workflow below, without waiting for approval between steps. Make the calls a senior PM and engineer would make, write each decision down (`outputs/decisions/`), and keep going. Stop and report only if blocked (missing access, a constraint conflict). Commit small, with clear messages, on branch `build`; push often; open one PR to `main` at the end.

Commit trailer:
```
Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
```

## Workflow and deliverables

`/pm-init` → `/opportunity-analysis` (with commercial value) → `/prd-draft` (+ `/prd-review-panel`, fix blockers) → `/journey-map` → build → `/decision-doc` for each architecture choice → `/name-audit` → `/portfolio-case-study` (draft only; the PM publishes it).

## Engineering

Python 3.11, `uv`, DuckDB, Pydantic, pytest, Streamlit. Langfuse tracing optional, a no-op without keys. Claude via the Anthropic SDK, model `claude-sonnet-5-5`, only when `ANTHROPIC_API_KEY` is set; every AI path also has an offline path, so tests and the demo run with no key. Patterns to reuse (read, don't copy blindly): github.com/alexandrecela10/secondaries-radar (bronze, silver, gold layers; lineage on every number; point in time; versioned rules; eval gate; Streamlit demo with Under the hood).
