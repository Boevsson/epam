"""Test data builders shared across test modules."""

from collections.abc import Sequence

from filings_qa.research.domain.retrieval import RetrievalHit
from filings_qa.shared_kernel.values import PassageId


def ranked(*passage_ids: str) -> list[RetrievalHit]:
    """One retriever's output: best first, with descending raw scores."""
    return [
        RetrievalHit(PassageId(pid), score=float(len(passage_ids) - position))
        for position, pid in enumerate(passage_ids)
    ]


def ids_of(hits: Sequence[RetrievalHit]) -> list[str]:
    return [hit.passage_id for hit in hits]


def score_of(passage_id: str, hits: Sequence[RetrievalHit]) -> float:
    return next(hit.score for hit in hits if hit.passage_id == passage_id)
