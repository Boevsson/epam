"""Rank fusion for hybrid retrieval: core domain logic, implemented as pure functions."""

from collections.abc import Iterable, Iterator, Mapping, Sequence
from types import MappingProxyType
from typing import Protocol

from filings_qa.research.domain.retrieval import RetrievalHit, SourceRank
from filings_qa.shared_kernel.values import PassageId


class FusionStrategy(Protocol):
    def fuse(self, rankings: Mapping[str, Sequence[RetrievalHit]], limit: int) -> list[RetrievalHit]:
        """Merge best-first rankings (keyed by retriever name) into one best-first list of at most `limit`."""
        ...


class ReciprocalRankFusion:
    """Reciprocal Rank Fusion (Cormack, Clarke & Buettcher, SIGIR 2009).

    ``score(d) = sum over retrievers r of w_r / (k + rank_r(d))``, with 1-based ranks.

    Only ranks are used, so retrievers whose raw scores live on different scales (BM25 vs cosine
    similarity) combine without calibration. A larger ``k`` flattens the curve, so agreement between
    retrievers outweighs any single top-1. The flip side: rank-only scores cannot say that *nothing*
    is relevant, so relevance gating needs another signal.
    """

    def __init__(self, k: int = 60, weights: Mapping[str, float] | None = None) -> None:
        if k < 1:
            raise ValueError(f"k must be >= 1, got {k}")
        weights = dict(weights or {})
        if any(weight < 0 for weight in weights.values()):
            raise ValueError(f"weights must be non-negative, got {weights}")
        self._k = k
        self._weights = weights

    def fuse(self, rankings: Mapping[str, Sequence[RetrievalHit]], limit: int) -> list[RetrievalHit]:
        if limit < 1:
            raise ValueError(f"limit must be >= 1, got {limit}")
        scores: dict[PassageId, float] = {}
        provenance: dict[PassageId, dict[str, SourceRank]] = {}
        for source in sorted(rankings):  # a fixed order keeps floating-point sums reproducible
            weight = self._weights.get(source, 1.0)
            for rank, hit in enumerate(_first_occurrences(rankings[source]), start=1):
                scores[hit.passage_id] = scores.get(hit.passage_id, 0.0) + weight / (self._k + rank)
                provenance.setdefault(hit.passage_id, {})[source] = SourceRank(rank, hit.score)
        best_first = sorted(scores, key=lambda pid: (-scores[pid], pid))  # ties broken by id
        return [
            RetrievalHit(pid, scores[pid], MappingProxyType(provenance[pid])) for pid in best_first[:limit]
        ]


def _first_occurrences(hits: Iterable[RetrievalHit]) -> Iterator[RetrievalHit]:
    seen: set[PassageId] = set()
    for hit in hits:
        if hit.passage_id not in seen:
            seen.add(hit.passage_id)
            yield hit


class WeightedScoreFusion:
    """Convex combination of min-max normalized scores: ``alpha * dense + (1 - alpha) * keyword``.

    Bruch, Gai & Ingber (ACM TOIS 2023) found that a tuned convex combination can beat RRF with only a few
    labeled queries; the evaluation harness compares both. A passage missing from one ranking scores 0 there.
    """

    def __init__(self, alpha: float = 0.5, *, dense: str = "dense", keyword: str = "bm25") -> None:
        if not 0 <= alpha <= 1:
            raise ValueError(f"alpha must be within [0, 1], got {alpha}")
        self._weights = {dense: alpha, keyword: 1 - alpha}

    def fuse(self, rankings: Mapping[str, Sequence[RetrievalHit]], limit: int) -> list[RetrievalHit]:
        if limit < 1:
            raise ValueError(f"limit must be >= 1, got {limit}")
        scores: dict[PassageId, float] = {}
        provenance: dict[PassageId, dict[str, SourceRank]] = {}
        for source in sorted(rankings):
            hits = list(_first_occurrences(rankings[source]))
            if not hits:
                continue
            low, high = min(h.score for h in hits), max(h.score for h in hits)
            weight = self._weights.get(source, 0.0)
            for rank, hit in enumerate(hits, start=1):
                normalized = (hit.score - low) / (high - low) if high > low else 1.0
                scores[hit.passage_id] = scores.get(hit.passage_id, 0.0) + weight * normalized
                provenance.setdefault(hit.passage_id, {})[source] = SourceRank(rank, hit.score)
        best_first = sorted(scores, key=lambda pid: (-scores[pid], pid))
        return [
            RetrievalHit(pid, scores[pid], MappingProxyType(provenance[pid])) for pid in best_first[:limit]
        ]
