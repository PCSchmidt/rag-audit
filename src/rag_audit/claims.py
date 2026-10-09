"""Deterministic claim decomposition and citation extraction (no model involved)."""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict

_CITE = re.compile(r"\[(\d+(?:\s*,\s*\d+)*)\]")
# Split after ., ! or ? followed by whitespace and an uppercase letter/digit/quote, keeping any
# trailing citation marker with its sentence ("... fact.[1] Next" and "... fact [1]. Next").
_BOUNDARY = re.compile(r"(?<=[.!?])(?:\s*\[\d+(?:\s*,\s*\d+)*\])*\s+(?=[\"'(\[]?[A-Z0-9])")


class Claim(BaseModel):
    """One sentence of the generated summary with the footnotes attached to it."""

    model_config = ConfigDict(frozen=True)

    index: int
    text: str
    citations: tuple[int, ...]
    start: int  # character offset of the sentence in the summary
    end: int


def extract_citations(sentence: str) -> tuple[int, ...]:
    """Citation numbers in order of first appearance, deduplicated."""
    seen: list[int] = []
    for match in _CITE.finditer(sentence):
        for part in match.group(1).split(","):
            number = int(part.strip())
            if number not in seen:
                seen.append(number)
    return tuple(seen)


def strip_citations(sentence: str) -> str:
    """Sentence text with footnote markers removed, whitespace normalised."""
    no_marks = _CITE.sub("", sentence)
    return re.sub(r"\s+([.,;:!?])", r"\1", re.sub(r"\s+", " ", no_marks)).strip()


def split_claims(summary: str) -> list[Claim]:
    """Split a summary into sentence-level claims, preserving character offsets."""
    claims: list[Claim] = []
    cursor = 0
    pieces: list[tuple[int, int]] = []
    for boundary in _BOUNDARY.finditer(summary):
        pieces.append((cursor, boundary.end()))
        cursor = boundary.end()
    pieces.append((cursor, len(summary)))
    for start, end in pieces:
        raw = summary[start:end]
        text = raw.strip()
        if not strip_citations(text):
            continue
        lead = len(raw) - len(raw.lstrip())
        claims.append(
            Claim(
                index=len(claims),
                text=text,
                citations=extract_citations(text),
                start=start + lead,
                end=start + lead + len(text),
            )
        )
    return claims
