# Results

**No model benchmarks have been run yet.** Nothing here is a claim about verification quality.

## Planned measurement (not done)

| Item | Protocol |
|---|---|
| Dataset | FEVER dev (claim + evidence), HaluEval QA/summarisation |
| Model | `cross-encoder/nli-deberta-v3-small`, thresholds frozen on a dev split before the test split is touched |
| Metrics | precision / recall of flagged unsupported claims, ECE of entailment probability, p50/p95 latency per claim on CPU |
| Report | confusion matrix, threshold sweep, failure cases (coreference, multi-sentence evidence) |

## What is verified today

- 9 tests pass (unit + hypothesis): offsets map back to source text, hash is deterministic and input-sensitive, HMAC verifies, score in [0, 100].
- `mypy --strict` clean.
