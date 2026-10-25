# LinkedIn project entry (draft)

**Name:** Portfolio Answer Desk

**One line:** A portfolio question desk for an LP's private equity team: correct, sourced answers to leaders' questions in minutes.

**Description (count with `wc -m` on the text below only):**

You're a portfolio analyst at a large LP, an investor in many private equity funds. The CIO asks how exposed you are to a company in the news. It sits behind a fund, a fund of funds, a co-investment and a stake bought second-hand, under three spellings, and the write-down is only in a manager letter. Finding it all takes the morning.

Portfolio Answer Desk gives you the number, every route, the definition and the date of every figure, ready to send. The AI only picks a governed metric; code computes every number and blocks any number it didn't compute.

I tested five data setups on 60 questions with known answers, in an offline test where fixed readers stand in for the AI. One shared foundation answered 60 of 60, against 18 for documents plus a chatbot. Expected time to a sendable answer: under a minute per question, against 84 minutes, under an assumed checking model. It showed no wrong number with a source; documents plus a chatbot showed 27.

Hypotheses tested:
1. If company spellings and holding routes are linked once, every route is found. Result: 20 of 20 event questions. Spelling, not hops, was what broke the semantic layer alone.
2. If each metric has one versioned definition, the committee pack matches last quarter's. Result: 20 of 20, same answer on every rerun and rephrasing.
3. If issues come from cited letters, none is missed. Result: 5 of 5 planted issues, each with its letter.

The graph earned its place only for links between people and managers, not for routes at this size.

Synthetic data, invented names. Live AI run and a timed test with analysts are next.

**Demo:** deploy pending (Streamlit Community Cloud).
