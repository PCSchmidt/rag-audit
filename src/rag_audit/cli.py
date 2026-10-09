"""CLI: `rag-audit --sources a.txt b.txt --summary s.txt [--fail-below 80]`."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from .auditor import FactualityAuditor
from .nli import LexicalOverlapNLI, NLIScorer


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="rag-audit", description=__doc__)
    parser.add_argument("--sources", nargs="+", required=True, type=Path)
    parser.add_argument("--summary", required=True, type=Path)
    parser.add_argument("--fail-below", type=float, default=None, help="exit 1 under this score")
    parser.add_argument(
        "--scorer", choices=["deberta", "lexical-test-double"], default="deberta"
    )
    args = parser.parse_args(argv)

    scorer: NLIScorer
    if args.scorer == "deberta":
        from .nli import CrossEncoderNLI

        scorer = CrossEncoderNLI()
    else:
        scorer = LexicalOverlapNLI()
    key = os.environ.get("RAG_AUDIT_SIGNING_KEY")
    auditor = FactualityAuditor(scorer, signing_key=key.encode() if key else None)
    report = auditor.audit(
        [p.read_text(encoding="utf-8") for p in args.sources],
        args.summary.read_text(encoding="utf-8"),
    )
    sys.stdout.write(report.model_dump_json(indent=2) + "\n")
    if args.fail_below is not None and report.factuality_score < args.fail_below:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
