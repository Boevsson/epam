"""Answers with claim-level attribution: every segment of text carries the citations that support it."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType

from filings_qa.research.domain.passage import Passage
from filings_qa.shared_kernel.errors import InvalidValueError
from filings_qa.shared_kernel.values import PassageId


@dataclass(frozen=True, slots=True)
class Citation:
    """A pointer to the exact supporting text (one or more sentences) of a passage."""

    passage_id: PassageId
    quote: str


@dataclass(frozen=True, slots=True)
class AnswerSegment:
    text: str
    citations: tuple[Citation, ...] = ()


@dataclass(frozen=True, slots=True)
class DraftAnswer:
    """What an answer generator produced, before the grounding policy has checked it."""

    segments: tuple[AnswerSegment, ...]
    generator: str
    model: str | None = None
    notice: str | None = None  # e.g. why the LLM was not used


class GroundingStatus(StrEnum):
    GROUNDED = "grounded"
    PARTIALLY_GROUNDED = "partially_grounded"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    EXTRACTIVE_FALLBACK = "extractive_fallback"  # no LLM: the most relevant sentences, quoted


@dataclass(frozen=True, slots=True)
class Evidence:
    """The passages given to answer generation, best first."""

    passages: tuple[Passage, ...]
    _by_id: Mapping[PassageId, Passage] = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not self.passages:
            raise InvalidValueError("evidence needs at least one passage")
        object.__setattr__(self, "_by_id", MappingProxyType({p.id: p for p in self.passages}))

    def get(self, passage_id: PassageId) -> Passage | None:
        return self._by_id.get(passage_id)


@dataclass(frozen=True, slots=True)
class Answer:
    """Invariant: every citation points into the evidence the answer was generated from."""

    status: GroundingStatus
    segments: tuple[AnswerSegment, ...]
    coverage: float
    evidence: Evidence
    generator: str
    model: str | None = None
    notice: str | None = None

    def __post_init__(self) -> None:
        for segment in self.segments:
            for citation in segment.citations:
                if self.evidence.get(citation.passage_id) is None:
                    raise InvalidValueError(f"citation to {citation.passage_id}, which is not in the evidence")

    @property
    def text(self) -> str:
        return "".join(segment.text for segment in self.segments)

    @classmethod
    def insufficient(cls, evidence: Evidence, message: str, generator: str = "none") -> "Answer":
        return cls(GroundingStatus.INSUFFICIENT_EVIDENCE, (AnswerSegment(message),), 0.0, evidence, generator)
