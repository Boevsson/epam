"""Retrieval results as the Research context sees them: ranked passages with provenance."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from filings_qa.shared_kernel.values import PassageId


@dataclass(frozen=True, slots=True)
class SourceRank:
    """Where one retriever placed a passage: 1-based rank plus that retriever's raw score."""

    rank: int
    score: float


_NO_PROVENANCE: Mapping[str, SourceRank] = MappingProxyType({})


@dataclass(frozen=True, slots=True)
class RetrievalHit:
    """A passage ranked for a query.

    ``score`` is only comparable within one ranked list: BM25 scores, cosine similarities and fused
    scores live on different scales. ``provenance`` records how each retriever ranked the passage,
    which is what makes hybrid results explainable.
    """

    passage_id: PassageId
    score: float
    provenance: Mapping[str, SourceRank] = field(default_factory=lambda: _NO_PROVENANCE, hash=False)
