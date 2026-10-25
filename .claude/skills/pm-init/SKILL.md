---
name: pm-init
description: Scaffold the PM OS workspace (context-library/ and outputs/ folders plus blank context templates) in the current product repo so every other PM OS skill has somewhere to read from and write to.
disable-model-invocation: false
user-invocable: true
---

## Quick Start

```
/pm-init                 → Scaffold context-library/ and outputs/ in the current repo
/pm-init --dry-run       → Show what would be created, create nothing
```

**What you get:** the standard PM OS folder structure committed to the product repo, empty except for `.gitkeep` files and two blank context templates. Idempotent: existing files are never overwritten.

**Time:** under a minute.

---

# /pm-init - Scaffold a PM OS workspace

PM OS is the shared engine (skills, templates, frameworks, voice). Each product repo owns its context and outputs. This skill creates that per-repo half.

## Steps

1. **Confirm the target.** The target is the root of the repo the user is working in (the folder containing `.git`). Never scaffold inside `{pm-os}` itself unless the user is explicitly working on PM OS as a product.

2. **Create the folders.** For each path below, create it if missing and add an empty `.gitkeep` so git tracks it:

   ```
   context-library/
   ├── strategy/        # product strategy docs (frameworks live in {pm-os}/frameworks/)
   ├── prds/            # finalized PRDs
   ├── research/        # user research, competitive analysis
   ├── decisions/       # decision logs
   ├── launches/        # launch plans, release notes
   ├── metrics/         # analytics reports, A/B tests
   ├── meetings/        # meeting notes
   └── other/
   outputs/
   ├── prds/  analyses/  decisions/  roadmaps/  prototypes/  journey-maps/
   ├── meeting-notes/  research-synthesis/  status-updates/  slack-messages/
   ├── weekly-plans/  weekly-reviews/  daily-plans/  mcp-integration-logs/
   └── skill-test-results/
   ```

3. **Copy the blank context templates** into `context-library/` under the names every skill looks for. Skip any that already exist:

   | From | To |
   |------|----|
   | `{pm-os}/templates/business-info-template.md` | `context-library/business-info-template.md` |
   | `{pm-os}/templates/stakeholder-template.md` | `context-library/stakeholder-template.md` |

4. **Write `context-library/README.md`** (skip if present) with three lines: what goes in each folder, that skills read from here and write to `outputs/`, and a reminder to fill in `business-info-template.md` first.

4b. **Ask the names policy (added 2026-10-25, PM correction).** One question: which real names and sources stay named and linked (public news, filings, public reports), and which must never appear (employer, clients, prospects, interview targets)? Add the answer as a "Names policy" section in `context-library/README.md`. Public sources are named and linked by default; anonymise only what the PM lists.

5. **Report.** List what was created and what was skipped. Then suggest the first two things to do:
   - Fill in `context-library/business-info-template.md` (company, product, stage, users). Every skill reads it.
   - Run `/prd-draft`, `/competitor-analysis`, or `/impact-sizing` on the current product.

## Rules

- Never overwrite an existing file. Print "exists, skipped" instead.
- Do not add `outputs/` to `.gitignore`. Outputs are drafts the PM reviews in PRs.
- If the repo already has some of the structure, only fill the gaps.
- With `--dry-run`, print the plan as a tree and stop.

## Example

```
/pm-init

Scaffolding PM OS workspace in sponsoryourwayvaluation/

Created:
  context-library/{strategy,prds,research,decisions,launches,metrics,meetings,other}/.gitkeep
  context-library/business-info-template.md
  context-library/stakeholder-template.md
  context-library/README.md
  outputs/{prds,analyses,decisions,...}/.gitkeep

Skipped (already present):
  none

Next: fill in context-library/business-info-template.md, then try /prd-draft.
```
