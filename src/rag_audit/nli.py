"""NLI scorers. The auditor depends only on the `NLIScorer` protocol."""

from __future__ import annotations

import re
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, model_validator


class NLIScores(BaseModel):
    """Probabilities over the three NLI labels; must sum to 1 (within tolerance)."""

    model_config = ConfigDict(frozen=True)

    entailment: float
    neutral: float
    contradiction: float

    @model_validator(mode="after")
    def _normalised(self) -> NLIScores:
        values = (self.entailment, self.neutral, self.contradiction)
        if any(v < 0.0 or v > 1.0 for v in values) or abs(sum(values) - 1.0) > 1e-3:
            raise ValueError(f"NLI scores must be probabilities summing to 1, got {values}")
        return self


class NLIScorer(Protocol):
    name: str

    def score(self, premise: str, hypothesis: str) -> NLIScores: ...


class CrossEncoderNLI:
    """Hugging Face cross-encoder NLI (default: cross-encoder/nli-deberta-v3-small).

    Requires the `nli` extra. Label order is read from the model config, never assumed.
    """

    def __init__(self, model_name: str = "cross-encoder/nli-deberta-v3-small") -> None:
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        self.name = model_name
        self._tokenizer: Any = AutoTokenizer.from_pretrained(model_name)
        self._model: Any = AutoModelForSequenceClassification.from_pretrained(model_name)
        self._model.eval()
        labels = {int(i): str(lbl).lower() for i, lbl in self._model.config.id2label.items()}
        wanted = {"entailment", "neutral", "contradiction"}
        if set(labels.values()) != wanted:
            raise ValueError(f"model labels {sorted(labels.values())} are not {sorted(wanted)}")
        self._labels = labels

    def score(self, premise: str, hypothesis: str) -> NLIScores:
        import torch

        batch = self._tokenizer(
            premise, hypothesis, return_tensors="pt", truncation=True, max_length=512
        )
        with torch.no_grad():
            probs = torch.softmax(self._model(**batch).logits[0], dim=-1).tolist()
        by_label = {self._labels[i]: float(p) for i, p in enumerate(probs)}
        return NLIScores(**by_label)


_WORD = re.compile(r"[a-z0-9]+")


class LexicalOverlapNLI:
    """Deterministic test double: entailment ~ fraction of hypothesis tokens in the premise.

    NOT a factuality model. It exists so the gate logic, hashing and CLI can be tested
    without downloading weights; never report its numbers as verification quality.
    """

    name = "lexical-overlap-test-double"

    def score(self, premise: str, hypothesis: str) -> NLIScores:
        hyp = set(_WORD.findall(hypothesis.lower()))
        if not hyp:
            return NLIScores(entailment=0.0, neutral=1.0, contradiction=0.0)
        overlap = len(hyp & set(_WORD.findall(premise.lower()))) / len(hyp)
        return NLIScores(entailment=overlap, neutral=1.0 - overlap, contradiction=0.0)
