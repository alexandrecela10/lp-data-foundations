# Intent: a trust pack for AI answers over a family office's documents

Author: Alexandre Cela. Status: draft.
Source: no opportunity analysis. This comes from the approved plan in `TRUST_PACK_M0.md` (v2, 2026-11-25).
Evidence: no family office has been interviewed. The pain is inferred from public signals: UAE data protection laws and the documents a family office typically holds.

## Problem

- A single family office in the UAE holds two kinds of sensitive data in one place: investment documents and the family's own records (identity documents, a foundation charter, succession plans).
- If staff ask an AI assistant questions over those documents, one bad answer can show a family member something they shouldn't see, or invent a number with no source.
- A leak here is personal, not only financial. A next-generation family member who reads a succession memo early is a family problem, not a data incident.
- Most demos of AI assistants show the answer and hide the controls. A principal or their CTO can't tell what the assistant was allowed to read, what it read, and why it said what it said.
- Concrete case (synthetic): the external lawyer asks "What did we commit to Fund X?" A system that filters after generating may already have put the commitment into the model's context. Number of times this happens today: unobserved.

## Proposed outcome

- Goes in: a question, and who is asking.
- Comes back: an answer where every claim cites a passage the asker may see, or "not found in the documents"; plus a record showing who asked, what they could see, what was retrieved, the scores and the versions used.
- Delivered as one interactive page, built from a real run, that walks one question through 12 controls. The page also teaches which UAE data law applies where, and how each control maps to classic data and ML practice.

What should change:
- Chunks retrieved from a room the asker can't see: unobserved today; target 0 in every eval question.
- Answers whose cited span isn't in the cited chunk: target 0 (citation accuracy at least 0.95).
- Questions that should be refused or abstained on and are: target at least 0.9.
- Planted instruction in a document changes the answer: target 0 times.

What must not get worse:
- Synthetic data only. No real family, person, ID number or company.
- The demo runs with no key and no network.
- The existing Answer Desk tests stay green.

## Affected users and systems

Users: the PM now, as a learner and in interviews. Later, a family office principal, CIO or CTO reading the page.
Systems: new `src/trustpack/` package and `trust_pack/` folder. Reused patterns: `answerdesk/foundations/search.py` (BM25), `answerdesk/contracts.py`, `answerdesk/governance.py`.

## Constraints

- Synthetic data, invented names, checked against real ones before use. Never name the PM's employer, clients, prospects or interviewers.
- "Synthetic data. Not investment advice." on every user-facing surface.
- No keys in the repo. Claude only behind `ANTHROPIC_API_KEY` plus an explicit flag; offline path by default.
- Lightweight: no Docker, no database server, no self-hosted tracing.
- Every legal statement links to the official text and is dated.

## Open questions

- Do family offices in the UAE actually let staff use AI assistants over family records today? Unobserved. If they don't, the page is about readiness, not risk.
- Which set-up is most common for a single family office: onshore, DIFC or ADGM? Unobserved. It decides which law the page leads with.
- Would a principal accept an offline answerer that abstains often, over a model that answers more but sometimes wrongly? Unobserved.
