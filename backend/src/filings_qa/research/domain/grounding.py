"""Decide how well an answer is supported by its evidence: accuracy and verifiability over fluency."""

import re

from filings_qa.research.domain.answer import (
    Answer,
    AnswerSegment,
    Citation,
    DraftAnswer,
    Evidence,
    GroundingStatus,
)

EXTRACTIVE_GENERATOR = "extractive"
_WORD = re.compile(r"[A-Za-z0-9]+")
_MIN_SUBSTANTIVE_WORDS = 5  # shorter segments ("According to the filing, ") are connective text


class GroundingPolicy:
    def __init__(self, min_coverage: float = 0.6) -> None:
        if not 0 <= min_coverage <= 1:
            raise ValueError(f"min_coverage must be within [0, 1], got {min_coverage}")
        self._min_coverage = min_coverage

    def assess(self, draft: DraftAnswer, evidence: Evidence) -> Answer:
        segments = tuple(
            AnswerSegment(s.text, tuple(c for c in s.citations if _supported(c, evidence)))
            for s in draft.segments
        )
        coverage = _coverage(segments)
        if draft.generator == EXTRACTIVE_GENERATOR:
            status = GroundingStatus.EXTRACTIVE_FALLBACK
        elif not any(segment.citations for segment in segments):
            status = GroundingStatus.INSUFFICIENT_EVIDENCE
        elif coverage < self._min_coverage:
            status = GroundingStatus.PARTIALLY_GROUNDED
        else:
            status = GroundingStatus.GROUNDED
        return Answer(status, segments, coverage, evidence, draft.generator, draft.model)


def _supported(citation: Citation, evidence: Evidence) -> bool:
    """Drop citations that point outside the evidence or quote text the passage does not contain."""
    passage = evidence.get(citation.passage_id)
    return passage is not None and _normalize(citation.quote) in _normalize(passage.text)


def _coverage(segments: tuple[AnswerSegment, ...]) -> float:
    substantive = [s for s in segments if len(_WORD.findall(s.text)) >= _MIN_SUBSTANTIVE_WORDS]
    total = sum(len(s.text) for s in substantive)
    cited = sum(len(s.text) for s in substantive if s.citations)
    return cited / total if total else 0.0


def _normalize(text: str) -> str:
    return " ".join(text.split()).lower()
