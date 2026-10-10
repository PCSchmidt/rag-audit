"""Worked example: audit a short briefing against two sources with the real NLI model.

Run: python examples/demo.py          (needs `pip install -e ".[nli]"`; first run downloads ~570 MB)
"""

from __future__ import annotations

from rag_audit import FactualityAuditor
from rag_audit.nli import CrossEncoderNLI

SOURCES = [
    # Callers should keep each passage self-contained: here the subject is named in every sentence.
    (
        "The Harbor Bridge opened to traffic in 1932. The Harbor Bridge carries six lanes of "
        "traffic across the harbour. The Harbor Bridge is 1,149 metres long."
    ),
    (
        "The Harbor Ferry service ended in 1960. Ridership on the Harbor Ferry had fallen "
        "sharply after the bridge opened."
    ),
]

SUMMARY = (
    "The Harbor Bridge opened in 1932 [1]. "
    "It carries eight lanes of traffic [1]. "
    "The ferry service ended in 1960 [2]. "
    "The bridge was designed by a famous architect. "
    "The ferry was replaced by a tunnel in 1975 [3]."
)


def main() -> None:
    report = FactualityAuditor(CrossEncoderNLI(), entail_threshold=0.55).audit(SOURCES, SUMMARY)
    print(f"factuality score: {report.factuality_score:.0f}%  ({report.n_supported}/{report.n_claims})")
    for r in report.results:
        ev = r.best_evidence
        span = f"  source {ev.source_index} chars {ev.start}-{ev.end}" if ev else ""
        print(f"  {r.verdict.value:<17} {r.claim.text}{span}")
    print(f"payload sha256: {report.payload_sha256}")


if __name__ == "__main__":
    main()
