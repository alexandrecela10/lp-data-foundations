---
name: name-audit
description: Find every real company, client, employer, prospect or competitor name in a repo before it goes public, propose neutral replacements, and apply them only after PM approval. Covers code, docs, filenames, demo data, test fixtures, domains, social links, PDF text, repo names and videos. Use before publishing a project, or when /portfolio-case-study runs.
user-invocable: true
disable-model-invocation: false
---

# /name-audit

Input: a repo path, plus names the PM already knows about (client, target employer, fund). Output: `outputs/portfolio/<slug>/name-audit.md`, then edits and a commit once approved.

**Start from the names policy (added 2026-10-25, PM correction).** Read the "Names policy" in `context-library/README.md` (written by `/pm-init`) or the project `CLAUDE.md`. Public sources the policy keeps (news, filings) stay named and linked; don't anonymise them by default. If there is no policy, ask the PM that one question first.

## Steps

1. **Collect candidates.** Names the PM gives, plus proper nouns found in the README, UI strings, prompts, seed data and test fixtures. Check each: is it a real company? Invented-sounding demo names (e.g. "NovaPay") often are.
2. **Search every place names hide.** Record file and line for each hit:

| Place | How |
|---|---|
| Code, prompts, UI strings | grep, case-insensitive |
| Docs, README, demo scripts | grep |
| Filenames | find by pattern |
| Seed data, SQL, fixtures, tests | grep. Fixtures often use real companies (e.g. Tabby, Rize) |
| Domains and social links | grep for `.io`, `.ai`, `.com`, `linkedin.com/` in demo data |
| PDF, slide and image text | extract text (e.g. `pypdf`) and grep; metadata titles too |
| Repo name, remote, Pages URL | `git remote -v` |
| Videos and screenshots | list them; the PM checks by eye |
| Footers | "Confidential", client logos, copyright lines |

3. **Propose replacements.**
   - Clients, targets and employers become neutral roles ("the investment team").
   - Demo companies become clearly fictional names ("Fintech A").
   - Demo domains use the reserved `.example` TLD.
   - Competitors become categories.
   - Public data sources stay (SEC, EY, Arcadis), because they back numbers.
4. **Wait for approval.** Present the list and edit nothing yet.
5. **Apply.**
   - Run the test suite before and after. Tests must still pass.
   - Rename files with `git mv`.
   - Fix any comment the rename made meaningless.
6. **Re-run the search.** Report what's left and why: PDFs with no source to regenerate, fixtures the PM chose to keep.
7. **Commit only if the PM asks.** Never push without approval.

## Output format

`name-audit.md`: status line, a table (where, current, proposed), names kept and why, repo hygiene found (untracked READMEs, logs, secrets in history).
