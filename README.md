# rag-audit

Deterministic factuality gate for RAG outputs. A generated summary is split into claims, each `[n]` footnote is mapped to the **exact character span** of the cited source that best supports it, and a local NLI cross-encoder decides `ENTAILMENT / NEUTRAL / CONTRADICTION`. Anything not entailed is flagged. The result is an `AuditReport` with a SHA-256 payload hash (optionally HMAC-signed).

**Status:** v0.1 scaffold. Gate logic, hashing and CLI are tested; model-quality benchmarks (FEVER / HaluEval) are **not yet run** - see [docs/RESULTS.md](docs/RESULTS.md).

## Design rule

The NLI model is probabilistic; it never decides anything on its own. Claim splitting, citation parsing, span alignment, thresholds, verdict assignment and hashing are plain deterministic code. An uncited claim, an out-of-range footnote, or a cited-but-not-entailed claim is always flagged.

## Use

```bash
uv pip install -e ".[nli,dev]"
rag-audit --sources doc1.txt doc2.txt --summary summary.txt --fail-below 80
```

```python
from rag_audit import FactualityAuditor
from rag_audit.nli import CrossEncoderNLI

report = FactualityAuditor(CrossEncoderNLI()).audit(sources, summary)
report.factuality_score, report.flagged, report.payload_sha256
```

`LexicalOverlapNLI` is a test double for unit tests only; do not report its output as verification quality.

## Verdicts

| Verdict | Meaning |
|---|---|
| SUPPORTED | a cited passage has entailment >= threshold (default 0.7) |
| CONTRADICTED | no support and a cited passage has contradiction >= 0.5 |
| UNSUPPORTED | cited, but nothing entails it |
| UNCITED | claim carries no footnote |
| INVALID_CITATION | footnote number outside `source_documents` |

## Checks

```bash
pytest          # unit + property-based (hypothesis)
mypy src tests  # strict
docker build -t rag-audit . && docker run --rm --network none rag-audit
```

## Limits

- Sentence-level passages: a claim needing two sentences of evidence can be marked UNSUPPORTED.
- DeBERTa-small truncates at 512 tokens per (passage, claim) pair.
- Coreference ("It spans...") is not resolved; the claim is judged as written.
- Related, not duplicated: VERA audits research papers; gate-enforced-rag does extractive citation gating without NLI.
