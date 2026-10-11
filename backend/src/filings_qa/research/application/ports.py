"""Ports of the Research context."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from filings_qa.research.domain.answer import DraftAnswer, Evidence
from filings_qa.research.domain.passage import Passage
from filings_qa.research.domain.question import Question
from filings_qa.research.domain.retrieval import RetrievalHit
from filings_qa.research.domain.scope import SearchScope
from filings_qa.shared_kernel.values import FilingId, FiscalYear, PassageId, Ticker


class Retriever(Protocol):
    """Contract (checked by shared contract tests): at most `limit` hits, best first, unique passage ids,
    every hit admitted by `scope`."""

    @property
    def name(self) -> str: ...

    def retrieve(self, query: str, scope: SearchScope, limit: int) -> Sequence[RetrievalHit]: ...


@dataclass(frozen=True, slots=True)
class FilingSummary:
    filing_id: FilingId
    company: str
    ticker: Ticker
    fiscal_year: FiscalYear
    aliases: tuple[str, ...]
    page_count: int
    passage_count: int


class PassageReader(Protocol):
    def get_many(self, ids: Sequence[PassageId]) -> list[Passage]:
        """Passages in the order of `ids`; unknown ids are skipped."""
        ...

    def filings(self) -> Sequence[FilingSummary]: ...


class AnswerGenerationUnavailableError(Exception):
    """The answer generator could not be reached or failed (rate limit, outage, timeout, refusal)."""


class AnswerGenerator(Protocol):
    def generate(self, question: Question, evidence: Evidence) -> DraftAnswer:
        """Contract: only cites passages contained in `evidence`. Raises AnswerGenerationUnavailableError."""
        ...
