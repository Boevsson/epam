"""Query expansion as a Decorator: any Retriever, searched with analyst terms translated to filing wording."""

from collections.abc import Sequence

from filings_qa.research.application.ports import Retriever
from filings_qa.research.domain.analyst_vocabulary import AnalystVocabulary
from filings_qa.research.domain.retrieval import RetrievalHit
from filings_qa.research.domain.scope import SearchScope


class QueryExpandingRetriever:
    def __init__(self, inner: Retriever, vocabulary: AnalystVocabulary) -> None:
        self._inner = inner
        self._vocabulary = vocabulary

    @property
    def name(self) -> str:
        return self._inner.name

    def retrieve(self, query: str, scope: SearchScope, limit: int) -> Sequence[RetrievalHit]:
        return self._inner.retrieve(self._vocabulary.expand(query), scope, limit)
