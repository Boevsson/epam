"""Hybrid retrieval as a Composite: a Retriever built from retrievers plus a fusion strategy."""

from collections.abc import Sequence

from filings_qa.research.application.ports import Retriever
from filings_qa.research.domain.fusion import FusionStrategy
from filings_qa.research.domain.retrieval import RetrievalHit
from filings_qa.research.domain.scope import SearchScope


class HybridRetriever:
    name = "hybrid"

    def __init__(self, retrievers: Sequence[Retriever], fusion: FusionStrategy, *, candidates: int = 50) -> None:
        self._retrievers = list(retrievers)
        self._fusion = fusion
        self._candidates = candidates

    def retrieve(self, query: str, scope: SearchScope, limit: int) -> Sequence[RetrievalHit]:
        rankings = {r.name: r.retrieve(query, scope, self._candidates) for r in self._retrievers}
        return self._fusion.fuse(rankings, limit)
