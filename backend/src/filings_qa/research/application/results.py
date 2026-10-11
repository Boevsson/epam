"""Results returned by the Research use cases (application DTOs, mapped to JSON by the API)."""

from collections.abc import Mapping
from dataclasses import dataclass, field

from filings_qa.research.domain.answer import AnswerSegment, GroundingStatus
from filings_qa.research.domain.passage import Passage
from filings_qa.research.domain.retrieval import RetrievalHit
from filings_qa.research.domain.scope import ResolvedScope


@dataclass(frozen=True, slots=True)
class EvidenceHit:
    passage: Passage
    hit: RetrievalHit


@dataclass(frozen=True, slots=True)
class AnswerResult:
    question: str
    status: GroundingStatus
    segments: tuple[AnswerSegment, ...]
    coverage: float
    evidence: tuple[EvidenceHit, ...]
    scope: ResolvedScope
    generator: str
    model: str | None = None
    notice: str | None = None
    timings_ms: Mapping[str, float] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SearchResult:
    query: str
    mode: str
    hits: tuple[EvidenceHit, ...]
    scope: ResolvedScope
