"""Use case: retrieval only, with a choice of retriever (debugging, evaluation, showing hybrid at work)."""

from collections.abc import Mapping
from dataclasses import dataclass, field

from filings_qa.research.application.ask_question import _with_passages
from filings_qa.research.application.ports import PassageReader, Retriever
from filings_qa.research.application.results import SearchResult
from filings_qa.research.application.scoping import resolve_scope
from filings_qa.research.domain.question import Question
from filings_qa.research.domain.scope import SearchScope


class UnknownSearchModeError(ValueError):
    """The requested search mode has no retriever."""


@dataclass(frozen=True, slots=True)
class SearchCommand:
    query: str
    mode: str = "hybrid"
    limit: int = 10
    scope: SearchScope = field(default_factory=SearchScope)


class SearchPassages:
    def __init__(self, retrievers: Mapping[str, Retriever], passages: PassageReader) -> None:
        self._retrievers = dict(retrievers)
        self._passages = passages

    @property
    def modes(self) -> tuple[str, ...]:
        return tuple(self._retrievers)

    def __call__(self, command: SearchCommand) -> SearchResult:
        retriever = self._retrievers.get(command.mode)
        if retriever is None:
            raise UnknownSearchModeError(
                f"unknown search mode {command.mode!r}; use one of {', '.join(self.modes)}"
            )
        query = Question(command.query)
        resolved = resolve_scope(self._passages, query.text, command.scope)
        hits = retriever.retrieve(query.text, resolved.scope, command.limit)
        return SearchResult(query.text, command.mode, _with_passages(hits, self._passages), resolved)
