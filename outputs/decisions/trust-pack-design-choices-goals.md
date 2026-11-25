# Goals: Trust Pack

Exit criteria (binary):
1. `make demo` runs from a clean clone with no key and no network.
2. `make eval` prints all metrics, saves `trust_pack/runs/<run_id>.json` with versions, and exits 1 if any gate threshold fails.
3. 0 passages from a forbidden room across all golden questions (tested).
4. Every answered question cites quotes that the citation check verified (tested).
5. `make replay ID=...` returns the same answer for a logged request.
6. `DATA_BOUNDARY.md` lists exactly one outbound flow, off by default.
7. `TRUST.md` has the mapping table, real numbers, and limitations including the missing judge calibration.
8. No real employer, client, prospect or interviewer names; invented names searched.
Passing bar: all 8.
