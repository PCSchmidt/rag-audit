# Results

Model: `cross-encoder/nli-deberta-v3-small`, CPU, via the full `FactualityAuditor.audit` path. Dataset: FEVER with gold/retrieved evidence (`copenlu/fever_gold_evidence`).

## Task

Each item is one claim cited as `[1]` to its evidence text. SUPPORTS should come back SUPPORTED. REFUTES and NOT ENOUGH INFO should be flagged (positive class = flagged). 600 items per label, sampled with a fixed seed.

## Protocol

1. **Dev** (FEVER validation, seed 0, 1,793 items): threshold sweep 0.05-0.95 on max-passage entailment; the threshold with best F1 was frozen to `results/frozen.json` (0.45) **before** any test item was scored.
2. **Test** (FEVER test split, seed 2, 1,798 items): run once, end to end through the auditor.

Reproduce: `python scripts/fever_benchmark.py dev` then `python scripts/fever_benchmark.py test` (needs `.[nli]` and `datasets`).

## Test results (threshold 0.45)

| Metric | Value |
|---|---|
| Precision of flagging unsupported claims | 0.802 |
| Recall of flagging unsupported claims | 0.960 |
| F1 | 0.874 (dev: 0.871) |
| Recall on REFUTES / NOT ENOUGH INFO | 0.968 / 0.952 |
| SUPPORTS correctly kept | 0.527 |
| REFUTES given verdict CONTRADICTED (rather than UNSUPPORTED) | 0.820 |
| ECE of max entailment as P(SUPPORTS) | 0.172 |
| Latency per claim, p50 / p95 | 45 ms / 106 ms |

95% binomial interval on the flagging precision is roughly +/- 2 points (n=1,798).

## Reading it

- The gate is **conservative**: it catches nearly all unsupported claims but wrongly flags almost half of supported ones (0.527 kept). That is the right direction for a safety gate, and an expensive one for a user who has to review the false flags.
- The dev F1 curve is flat from 0.05 to 0.95 (0.862-0.871) because the model's entailment scores are close to bimodal (median 0.82 for SUPPORTS, 0.0 for the others). The threshold therefore matters little; do not read 0.45 as a tuned optimum.
- Multi-sentence evidence is **not** the explanation: items with one evidence sentence were kept at 52.8% and items with two or more at 52.1%. What does cause the misses is untested; likely candidates are FEVER sentences that lose their subject without the page title and claims that need world knowledge, but neither was measured.
- 82% of refuted claims receive the more informative CONTRADICTED verdict.
- ECE 0.17 means the raw entailment probability is overconfident as a probability of support; do not present it as calibrated.

## An invalid first run, kept for the record

The first test run reported recall 1.0, 0 supported claims and 20 microsecond latency. The model was never called: the claim splitter turned `"claim. [1]"` into a claim plus a citation-only fragment, so every claim was UNCITED. This was a library bug, fixed in `claims.py` with a regression test. The run exposed no model scores, so the frozen threshold was not influenced; the test split was re-sampled with a new seed (2) and run once. The invalid outputs are in `results/test_run1_INVALID_*`.

## Not measured

HaluEval, other NLI models (the roadmap names `roberta-large-snli_mnli_fever_anli`), summary-length inputs with several claims per document, non-Wikipedia text, adversarial or paraphrased claims, GPU latency.

## Verified

10 tests (unit + hypothesis), `mypy --strict`, ruff.
