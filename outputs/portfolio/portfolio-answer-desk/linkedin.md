# LinkedIn project entry (draft)

**Name:** Portfolio Answer Desk

**One line:** When the CIO asks about the portfolio, you send the right number, with its sources, in minutes.

**Description (count with `wc -m` on the text below only):**

You're an analyst at a large LP, an investor in many private equity funds. The CIO wants an answer before the 09:00 meeting. Finding it takes hours, and two analysts can send two different numbers.

Portfolio Answer Desk gives you one number, with its sources, ready to send. The AI reads the question. Code does the sums.

I tested five ways to organise the same data on 60 questions with known answers, live with Claude Sonnet 5.5. The best got 60 of 60 right, against 7 for an AI chatbot reading the documents, with no wrong number shown next to a source.

1. Company in the news: if every spelling links to one company, code finds every holding. 20 of 20, about 50 seconds each.
2. Committee pack: if each measure is written down once, the same question gets the same number. 100%.
3. Manager decision: if problems are quoted from the letters, none is missed. 5 of 5.

Synthetic data, invented names. Not investment advice.

**Demo:** https://portfolio-answer-desk.streamlit.app
