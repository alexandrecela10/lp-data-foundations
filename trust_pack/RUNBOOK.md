# Runbook

Synthetic data. Not investment advice.

## A wrong answer

1. **Find the trace.** Search `trust_pack/logs/audit.jsonl` by request ID or question.
2. **Classify.** Retrieval (the right passage was not in the top 5), generation (it was, and the answer chose the wrong sentence), data quality (the document was wrong or rejected), or access (the user should or should not see it).
3. **Add it to the golden set** with the expected answer, so the fix is measured.
4. **Fix one thing** and bump its version in `registry.yaml`.
5. **Pass the gate:** `make eval`, then a fresh holdout.
6. **Release.** Rollback means restoring the previous `registry.yaml`; every trace records the versions it used. `make replay ID=...` shows whether an old answer changes.

**Worked example (t15).** "Who receives the Dubai residence under the letter of wishes?" got "Omar Ardenvale should receive the holding company shares once he turns 30." The right passage (G06-c1) was in the top 5, so this is generation: the rules matched "receive" in the wrong sentence. Left unfixed in this build.

## A suspected leak

1. **Disable** the assistant for the affected room, or for everyone if the scope is unclear.
2. **Query the audit log:** which users, which passage IDs, which answers, since when.
3. **Notify** the principal and the data protection lead, and the regulator if the office's zone requires it (PDPL onshore, DIFC or ADGM rules in those zones).
