# LinkedIn project entry: Trust Pack (draft)

**Name:** Trust Pack

**Description (under 2,000 characters):**

Ask a family office's documents a question and get a quoted answer limited to what you are allowed to see, with evidence for every check.

The problem: a single family office holds fund reports next to the family's own records: passports, a foundation charter, a succession memo. An AI assistant over those documents can show the wrong person the wrong page, state a number with no source, or follow an instruction planted in a fund letter.

Who it is for: the CTO or head of data of a single family office in the UAE, and the principal who decides whether staff may use AI on family records.

What I built: a checking layer with 12 controls, from a contract every document must meet to a chained audit log that rebuilds any answer. Access is checked inside the search, before ranking. ID and bank numbers are removed before indexing. Answers print only quotes checked against their passage. A red-team tab lets you try your own attacks in the page.

Results on made-up data, offline:
- 0 answers quoted a document the asker may not see, across 64 requests, 13 of them attacks.
- 0 of 12 passport, ID and bank numbers reachable by any question.
- 51 of 51 answers rebuilt exactly from the audit log.
- On 10 new questions, 0 wrong facts; 3 of 6 answerable ones answered, the rest said "not found".

What it doesn't prove yet: real documents, Arabic search, a login, and the live AI path. The red-team review names 9 open gaps.

Demo and case study: https://alexandrecela10.github.io/projects/trust-pack/
Code: https://github.com/alexandrecela10/lp-data-foundations/tree/main/trust_pack

Made-up data. Not investment advice.
