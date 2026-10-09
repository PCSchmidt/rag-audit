from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from rag_audit import FactualityAuditor, LexicalOverlapNLI, Verdict, split_claims, verify_signature
from rag_audit.auditor import passages
from rag_audit.claims import extract_citations
from rag_audit.nli import NLIScores

SOURCES = [
    "The bridge opened in 1932. It spans the harbour and carries six lanes of traffic.",
    "The ferry service ended in 1960. Ridership had fallen sharply.",
]


class FixedNLI:
    """Returns scripted scores keyed on hypothesis substring."""

    name = "fixed"

    def __init__(self, table: dict[str, NLIScores]) -> None:
        self.table = table

    def score(self, premise: str, hypothesis: str) -> NLIScores:
        for key, value in self.table.items():
            if key in hypothesis:
                return value
        return NLIScores(entailment=0.0, neutral=1.0, contradiction=0.0)


def test_split_claims_offsets_and_citations() -> None:
    summary = "The bridge opened in 1932 [1]. The ferry ended in 1960 [2]. Unsourced remark."
    claims = split_claims(summary)
    assert [c.citations for c in claims] == [(1,), (2,), ()]
    for c in claims:
        assert summary[c.start : c.end] == c.text


def test_multi_citation_parse() -> None:
    assert extract_citations("x [1, 2] y [2] z [3]") == (1, 2, 3)


def test_verdicts_cover_every_branch() -> None:
    nli = FixedNLI(
        {
            "1932": NLIScores(entailment=0.95, neutral=0.04, contradiction=0.01),
            "1960": NLIScores(entailment=0.05, neutral=0.05, contradiction=0.9),
            "seven": NLIScores(entailment=0.2, neutral=0.7, contradiction=0.1),
        }
    )
    summary = (
        "The bridge opened in 1932 [1]. The ferry ended in 1960 [1]. "
        "It has seven lanes [1]. The tolls are high. A claim cites nothing real [9]."
    )
    report = FactualityAuditor(nli).audit(SOURCES, summary)
    assert [r.verdict for r in report.results] == [
        Verdict.SUPPORTED,
        Verdict.CONTRADICTED,
        Verdict.UNSUPPORTED,
        Verdict.UNCITED,
        Verdict.INVALID_CITATION,
    ]
    assert report.factuality_score == 20.0
    assert len(report.flagged) == 4


def test_evidence_span_maps_back_to_source() -> None:
    report = FactualityAuditor(LexicalOverlapNLI()).audit(
        SOURCES, "The ferry service ended in 1960 [2]."
    )
    ev = report.results[0].best_evidence
    assert ev is not None
    assert SOURCES[1][ev.start : ev.end] == ev.passage


def test_hash_deterministic_and_sensitive() -> None:
    a = FactualityAuditor(LexicalOverlapNLI())
    s = "The bridge opened in 1932 [1]."
    assert a.audit(SOURCES, s).payload_sha256 == a.audit(SOURCES, s).payload_sha256
    changed = [SOURCES[0] + " Edited.", SOURCES[1]]
    assert a.audit(changed, s).payload_sha256 != a.audit(SOURCES, s).payload_sha256


def test_signature_roundtrip() -> None:
    report = FactualityAuditor(LexicalOverlapNLI(), signing_key=b"k").audit(SOURCES, "A fact [1].")
    assert verify_signature(report, b"k")
    assert not verify_signature(report, b"wrong")


@given(st.text(max_size=400))
def test_split_claims_never_crashes_and_offsets_valid(summary: str) -> None:
    for c in split_claims(summary):
        assert summary[c.start : c.end] == c.text


@given(st.text(max_size=300))
def test_passages_offsets_valid(doc: str) -> None:
    for start, end, text in passages(doc):
        assert doc[start:end] == text


@given(st.lists(st.text(max_size=80), min_size=1, max_size=3), st.text(max_size=200))
def test_score_in_range_and_flags_consistent(sources: list[str], summary: str) -> None:
    report = FactualityAuditor(LexicalOverlapNLI()).audit(sources, summary)
    assert 0.0 <= report.factuality_score <= 100.0
    assert report.n_supported + len(report.flagged) == report.n_claims


def test_citation_after_sentence_punctuation_stays_with_claim() -> None:
    # Regression: "fact. [1]" used to split into a claim and a citation-only fragment (UNCITED).
    (claim,) = split_claims("The bridge opened in 1932. [1]")
    assert claim.citations == (1,)
    assert [c.citations for c in split_claims("First fact. [1] Second fact. [2]")] == [(1,), (2,)]
