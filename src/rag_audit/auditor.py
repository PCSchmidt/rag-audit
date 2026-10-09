"""FactualityAuditor: every claim is verified against the exact cited span, or flagged."""

from __future__ import annotations

import hashlib
import hmac
import json
import re
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .claims import Claim, split_claims, strip_citations
from .nli import NLIScorer, NLIScores

_PASSAGE_SPLIT = re.compile(r"(?<=[.!?])\s+")


class Verdict(str, Enum):
    SUPPORTED = "SUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    UNSUPPORTED = "UNSUPPORTED"  # cited, but no cited passage entails the claim
    UNCITED = "UNCITED"
    INVALID_CITATION = "INVALID_CITATION"  # footnote points outside source_documents


class Evidence(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_index: int  # 1-based, matches the footnote number
    start: int  # character offsets into that source document
    end: int
    passage: str
    scores: NLIScores


class ClaimResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    claim: Claim
    verdict: Verdict
    best_evidence: Evidence | None = None


class AuditReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    factuality_score: float = Field(ge=0.0, le=100.0)
    n_claims: int
    n_supported: int
    results: tuple[ClaimResult, ...]
    flagged: tuple[ClaimResult, ...]
    scorer: str
    entail_threshold: float
    contradict_threshold: float
    payload_sha256: str
    signature: str | None = None  # HMAC-SHA256 over payload_sha256, when a key was supplied


def passages(document: str) -> list[tuple[int, int, str]]:
    """Sentence-level passages with character offsets, so evidence maps back to the source."""
    spans: list[tuple[int, int, str]] = []
    cursor = 0
    for piece in _PASSAGE_SPLIT.split(document):
        start = document.find(piece, cursor)
        if start < 0 or not piece.strip():
            continue
        cursor = start + len(piece)
        spans.append((start, cursor, piece))
    return spans


def _canonical(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


class FactualityAuditor:
    def __init__(
        self,
        scorer: NLIScorer,
        entail_threshold: float = 0.7,
        contradict_threshold: float = 0.5,
        signing_key: bytes | None = None,
    ) -> None:
        if not 0.0 < entail_threshold <= 1.0 or not 0.0 < contradict_threshold <= 1.0:
            raise ValueError("thresholds must be in (0, 1]")
        self.scorer = scorer
        self.entail_threshold = entail_threshold
        self.contradict_threshold = contradict_threshold
        self._key = signing_key

    def _best_evidence(self, claim_text: str, number: int, document: str) -> Evidence | None:
        best: Evidence | None = None
        for start, end, passage in passages(document):
            scores = self.scorer.score(passage, claim_text)
            if best is None or scores.entailment > best.scores.entailment:
                best = Evidence(
                    source_index=number, start=start, end=end, passage=passage, scores=scores
                )
        return best

    def _judge(self, claim: Claim, sources: list[str]) -> ClaimResult:
        if not claim.citations:
            return ClaimResult(claim=claim, verdict=Verdict.UNCITED)
        if any(n < 1 or n > len(sources) for n in claim.citations):
            return ClaimResult(claim=claim, verdict=Verdict.INVALID_CITATION)
        text = strip_citations(claim.text)
        candidates = [
            ev
            for n in claim.citations
            if (ev := self._best_evidence(text, n, sources[n - 1])) is not None
        ]
        if not candidates:
            return ClaimResult(claim=claim, verdict=Verdict.UNSUPPORTED)
        best = max(candidates, key=lambda e: e.scores.entailment)
        if best.scores.entailment >= self.entail_threshold:
            return ClaimResult(claim=claim, verdict=Verdict.SUPPORTED, best_evidence=best)
        worst = max(candidates, key=lambda e: e.scores.contradiction)
        if worst.scores.contradiction >= self.contradict_threshold:
            return ClaimResult(claim=claim, verdict=Verdict.CONTRADICTED, best_evidence=worst)
        return ClaimResult(claim=claim, verdict=Verdict.UNSUPPORTED, best_evidence=best)

    def audit(self, source_documents: list[str], generated_summary: str) -> AuditReport:
        results = tuple(self._judge(c, source_documents) for c in split_claims(generated_summary))
        supported = sum(r.verdict is Verdict.SUPPORTED for r in results)
        score = 0.0 if not results else round(100.0 * supported / len(results), 6)
        payload = {
            "sources_sha256": [hashlib.sha256(s.encode()).hexdigest() for s in source_documents],
            "summary_sha256": hashlib.sha256(generated_summary.encode()).hexdigest(),
            "scorer": self.scorer.name,
            "entail_threshold": self.entail_threshold,
            "contradict_threshold": self.contradict_threshold,
            "claims": [
                {
                    "text": r.claim.text,
                    "verdict": r.verdict.value,
                    "entailment": None
                    if r.best_evidence is None
                    else round(r.best_evidence.scores.entailment, 6),
                    "span": None
                    if r.best_evidence is None
                    else [r.best_evidence.source_index, r.best_evidence.start, r.best_evidence.end],
                }
                for r in results
            ],
        }
        digest = hashlib.sha256(_canonical(payload)).hexdigest()
        signature = (
            None if self._key is None else hmac.new(self._key, digest.encode(), "sha256").hexdigest()
        )
        return AuditReport(
            factuality_score=score,
            n_claims=len(results),
            n_supported=supported,
            results=results,
            flagged=tuple(r for r in results if r.verdict is not Verdict.SUPPORTED),
            scorer=self.scorer.name,
            entail_threshold=self.entail_threshold,
            contradict_threshold=self.contradict_threshold,
            payload_sha256=digest,
            signature=signature,
        )


def verify_signature(report: AuditReport, key: bytes) -> bool:
    if report.signature is None:
        return False
    expected = hmac.new(key, report.payload_sha256.encode(), "sha256").hexdigest()
    return hmac.compare_digest(expected, report.signature)
