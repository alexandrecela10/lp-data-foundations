# LinkedIn project entry (draft)

**Name:** Portfolio Answer Desk

**One line:** A portfolio question desk for an LP's private equity team: correct, sourced answers to leaders' questions in minutes.

**Description (count with `wc -m` on the text below only):**

You're a portfolio analyst at a large LP, an investor in many private equity funds. The CIO asks how exposed you are to a company in the news. It sits behind a fund, a fund of funds, a co-investment and a stake bought second-hand, under three spellings, and the write-down is only in a manager letter. Finding it all takes the morning.

Portfolio Answer Desk gives you the number, every route, the definition and the date of every figure, ready to check and send. The AI only reads the question and picks an agreed calculation; code computes every number and blocks any number it didn't compute.

I tested five data setups on 60 questions with known answers, offline and then live with Claude Sonnet 5.5 reading every question. The setup with agreed definitions, a company identity table and a graph answered 60 of 60 live, against 7 for documents plus a chatbot and 11 for AI-written SQL. It showed no wrong number with a source, and gave the same answer when every question was asked again.

Hypotheses tested:
1. If company spellings and holding routes are linked once, every route is found. Result: 20 of 20 event questions, offline and live. Spelling, not hops, was what broke the semantic layer alone.
2. If each metric has one versioned definition, the committee pack matches last quarter's. Result: 20 of 20, same answer on every rerun.
3. If issues come from cited letters, none is missed. Result: 5 of 5 planted issues, each with its letter.

On routes the graph tied the identity table, so it is kept for links between people and managers.

Synthetic data, invented names. A timed test with analysts is next.

**Demo:** deploy pending (Streamlit Community Cloud).
