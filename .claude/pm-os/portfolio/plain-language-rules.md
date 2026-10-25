# Plain-language rules for the portfolio (Alex, 2026-10-02)

Reader: a smart person outside finance. A software engineer, a recruiter, a friend. They should understand every sentence on first read.

## Rules

1. **Plain words first.** Replace jargon with everyday words. "Lender's valuation of a loan" instead of "mark". "Interest payment" instead of "coupon". "Investment committee" instead of "IC". "The fund's own investors" instead of "LPs".
2. **Explain the terms you keep.** If the persona really uses a term (BDC, non-accrual, ARR, runway), keep it, and explain it the first time in brackets in 8 words or fewer. Example: "BDC (a stock-listed fund that lends to private companies)".
3. **One concrete example per problem.** Show the problem with a specific situation and a number. Example: "A fund gets around 50 pitch decks a week. The best one can sit unread behind 49 others." When you explain a rule or concept, add the counterfactual: what would happen without it (added 2026-10-25).
4. **People, not roles.** "A junior investor at a startup fund" beats "VC analyst". "The head of the fund" beats "VC CEO".
5. **Short sentences.** One idea each, about 20 words maximum. No intros, no recaps, no hype.
6. **Keep the facts exactly.** Every number, link, file name, metric and claim stays as it is. Don't add numbers. Don't change meaning. Mark anything uncertain the same way the page already does ("assumed", "unobserved").
7. **Keep the structure.** Same sections, same cards, same order, same HTML layout and styles. Only the words change.
8. **Add a "Terms on this page" box** right after the "For" section (or after "Who" on Deck Rank): 4 to 8 terms, one plain line each.
9. **Voice rules still apply** (CLAUDE.md): no em dashes ever. Never: delve, leverage, utilize, unlock, harness, streamline, robust, cutting-edge, seamless, instant, powerful, effortless. Factual, not salesy.
10. **LinkedIn entries:** same rules, written as plain sentences (no arrows or pseudo-code). Description 2,000 characters max, measured with `wc -m` on the description only.

## Check before finishing

- Read the top of the page as an outsider: can you say what problem it solves, for whom, in one breath?
- Count of `href=` links is unchanged. Every number from the old version is still present.
- `grep -c "—"` returns 0.
