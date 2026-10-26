# LinkedIn project entry (draft)

**Name:** Portfolio Answer Desk

**One line:** When the CIO asks about the portfolio, you send the right number, with its sources, in minutes.

**Description (count with `wc -m` on the text below only):**

You're an analyst at a large LP, an investor in many private equity funds. At 08:12 the CIO asks how much you have in a company that's in the news. You own part of it 5 ways: through your own fund, twice through a fund that invests in other funds, through a fund stake bought from another investor, and next to a fund in a co-investment. Managers spell it 3 ways, and a letter from 10 September cut its value to 40%. Search one name and you send the wrong number.

Portfolio Answer Desk gives you the total, each way you own it, and the source, definition and date of every figure. The AI only reads the question. Code does every sum, and the answer never shows a number the code didn't calculate.

I tested five setups on 60 questions with known answers, with Claude Sonnet 5.5 reading each one. The best was agreed definitions, a list linking every spelling of a company, and a graph: 60 of 60 right. An AI chatbot reading the documents got 7 right, and an AI writing database queries got 11. The best setup never showed a wrong number next to a source and gave the same answer when asked again.

What I learned:
1. Spelling broke the answers, not the number of funds in between. Once every spelling pointed to one company, all 20 company questions were right.
2. Writing each measure down once, with a version number, made the committee pack match itself: 20 of 20, same answer every time.
3. Quoting problems straight from managers' letters missed none: 5 of 5.

The graph only beat the plain spelling list on 2 questions, about where former partners went. For company questions you don't need it.

Synthetic data, invented names. Not investment advice. Next: time real analysts on the same questions.

**Demo:** https://portfolio-answer-desk.streamlit.app
