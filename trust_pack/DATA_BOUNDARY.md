# Data boundary

Every flow of data in the Trust Pack. Config: `sovereignty.yaml`. Synthetic data. Not investment advice.

| # | From | To | What | When | Leaves the machine? |
|---|---|---|---|---|---|
| 1 | `trust_pack/data/room/*.md` | Index in memory | Accepted documents, PII redacted | Every run | No |
| 2 | Contract check | Reject list in the run file | Document ID and reason only | Every run | No |
| 3 | Index | Answer step | Top 5 passages the asker may see | Every question | No |
| 4 | Answer step | `trust_pack/logs/audit.jsonl` (git-ignored) | Request, versions, passage IDs and hashes, answer | Every question | No |
| 5 | Eval | `trust_pack/runs/*.json` | Metrics, versions, answers | `make eval` | No |
| 6 | Answer step | `api.anthropic.com` (model `claude-sonnet-5-5`) | Question and up to 5 non-restricted, redacted passages | Only with `ANTHROPIC_API_KEY` and `TRUSTPACK_LIVE=1` | **Yes, the one outbound flow** |

**Flow 6, terms.** Under the provider's commercial terms, API inputs are not used for training (check the current text before any real use). Retention follows the provider default. Zero data retention needs a separate agreement and is not assumed. Restricted passages (family governance) are never sent, even in live mode. The committed eval ran with flow 6 off.

**Not present by design:** hosted tracing, hosted embeddings, analytics or telemetry, any other outbound endpoint.
