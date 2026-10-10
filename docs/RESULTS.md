# Results

Dataset: FEVER with gold/retrieved evidence (`copenlu/fever_gold_evidence`). All runs go through the full `FactualityAuditor.audit` path on CPU.

## Task

Each item is one claim cited as `[1]` to its evidence text. SUPPORTS should come back SUPPORTED. REFUTES and NOT ENOUGH INFO should be flagged (positive class = flagged). 600 items per label.

## Protocol

1. **Dev** (FEVER validation, seed 0, ~1,790 items): sweep the entailment threshold 0.05-0.95; the best-F1 threshold is frozen **per condition** before any test item is scored.
2. **Test** (FEVER test split, ~1,800 items): run once per condition.

Reproduce: `bash scripts/run_ablation.sh` (needs `.[nli]` and `datasets`). Raw scores are in `results/`.

## 2 x 2 ablation (test split, seed 3, n = 1,800 for every cell)

Factors: NLI model (`nli-deberta-v3-small` vs `-base`) and whether each evidence sentence is prefixed with its Wikipedia page title (`"Title: sentence"`). The same 1,800 items are used in all four cells.

| Model | Page titles | Frozen threshold | Precision | Recall | F1 | Supported claims kept | ECE | Latency p50 / p95 |
|---|---|---|---|---|---|---|---|---|
| small | no | 0.45 | 0.813 | 0.946 | 0.874 | 56.5% | 0.166 | 44 / 102 ms |
| small | yes | 0.55 | 0.914 | 0.927 | 0.920 | 82.5% | 0.090 | 46 / 110 ms |
| base | no | 0.15 | 0.842 | 0.945 | 0.890 | 64.5% | 0.150 | 88 / 211 ms |
| base | yes | 0.60 | 0.934 | 0.932 | 0.933 | 86.8% | 0.081 | 95 / 247 ms |

Precision/recall are for flagging unsupported claims. A 95% binomial interval on a precision of about 0.9 at this n is roughly +/- 1.5-2 points, so the small-vs-base difference *with titles* (F1 0.920 vs 0.933) is within noise; the with-vs-without-titles difference is not.

## Findings

1. **Missing context, not model size, caused most of the false flags.** Adding the page title to each evidence sentence raised the share of supported claims kept from 56.5% to 82.5% on the small model (+26 points) and from 64.5% to 86.8% on the base model, with no latency cost and a lower ECE. Going from small to base without titles gained only 8 points of retention and doubled latency.
2. **Small plus titles is the best cost/quality point measured**: F1 0.920 at 46 ms versus base plus titles 0.933 at 95 ms.
3. **Stated limitation, revised.** Evidence sentences must carry their subject. Callers should prefix passages with a document title or equivalent context; the library does not add context itself.
4. **Recall of unsupported claims stays high in every cell** (0.93-0.95); the titles improve precision and retention without losing the gate's catch rate.
5. **Thresholds are not stable across conditions** (0.15 to 0.60) because the dev F1 curve is nearly flat when scores are close to bimodal; do not read any single threshold as an optimum.
6. About 83% of REFUTES claims receive the more informative CONTRADICTED verdict in all cells.
7. ECE of 0.08-0.17 means the raw entailment probability is overconfident as a probability of support; do not present it as calibrated.

## Earlier baseline run (small, no titles, test seed 2)

Same protocol, different test sample: F1 0.874, precision 0.802, recall 0.960, supported kept 52.7%. An earlier hypothesis that multi-sentence evidence caused the false flags was tested and rejected (single-sentence 52.8% kept, multi-sentence 52.1%).

## An invalid first run, kept for the record

The first test run reported recall 1.0, zero supported claims and 20 microsecond latency: the model was never called. The claim splitter turned `"claim. [1]"` into a claim plus a citation-only fragment, so every claim was UNCITED. Fixed in `claims.py` with a regression test. The run exposed no model scores, so the frozen threshold was not influenced; the test split was re-sampled with a new seed. Outputs: `results/test_run1_INVALID_*`.

## Not measured

HaluEval; other NLI models (the roadmap's `roberta-large-snli_mnli_fever_anli` was skipped on purpose because it was trained on FEVER, which would contaminate this benchmark, and its label names differ); multi-claim summaries; non-Wikipedia text; adversarial or paraphrased claims; GPU latency.

## Verified

10 tests (unit + hypothesis), `mypy --strict`, ruff.
