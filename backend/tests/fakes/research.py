"""In-memory implementations of the Research ports."""

from collections.abc import Callable, Sequence

from filings_qa.infrastructure.text_analysis import tokenize
from filings_qa.research.application.ports import AnswerGenerationUnavailableError, FilingSummary
from filings_qa.research.domain.answer import AnswerSegment, Citation, DraftAnswer, Evidence
from filings_qa.research.domain.passage import Passage
from filings_qa.research.domain.question import Question
from filings_qa.research.domain.retrieval import RetrievalHit, SourceRank
from filings_qa.research.domain.scope import SearchScope
from filings_qa.shared_kernel.values import FilingId, FiscalYear, ItemCode, PageRange, PassageId, Ticker

COMPANY_NAMES = {"AMD": "Advanced Micro Devices, Inc.", "PFE": "Pfizer Inc.", "PEP": "PepsiCo, Inc."}


def make_passage(
    passage_id: str,
    *sentences: str,
    ticker: str = "AMD",
    year: int = 2022,
    item: ItemCode = ItemCode.RISK_FACTORS,
    page: int = 10,
) -> Passage:
    return Passage(
        id=PassageId(passage_id),
        filing_id=FilingId(passage_id.split("#")[0]),
        company=COMPANY_NAMES.get(ticker, f"{ticker} Inc."),
        ticker=Ticker(ticker),
        fiscal_year=FiscalYear(year),
        item=item,
        pages=PageRange.single(page),
        sentences=sentences or ("Some text.",),
    )


class InMemoryPassageReader:
    def __init__(self, passages: Sequence[Passage], filings: Sequence[FilingSummary] = ()) -> None:
        self._passages = {p.id: p for p in passages}
        self._filings = list(filings) or _summaries(passages)

    def get_many(self, ids: Sequence[PassageId]) -> list[Passage]:
        return [self._passages[i] for i in ids if i in self._passages]

    def filings(self) -> Sequence[FilingSummary]:
        return self._filings

    def all(self) -> list[Passage]:
        return list(self._passages.values())


def _summaries(passages: Sequence[Passage]) -> list[FilingSummary]:
    by_filing: dict[FilingId, list[Passage]] = {}
    for passage in passages:
        by_filing.setdefault(passage.filing_id, []).append(passage)
    return [
        FilingSummary(
            fid, ps[0].company, ps[0].ticker, ps[0].fiscal_year, _aliases(ps[0].company), 100, len(ps)
        )
        for fid, ps in by_filing.items()
    ]


def _aliases(company: str) -> tuple[str, ...]:
    """The company name and its first word ("Pfizer Inc." -> "Pfizer"), like corpus.yaml aliases."""
    return (company, company.split()[0].rstrip(","))


class StubRetriever:
    """Returns fixed hits (filtered by scope when a reader is given) and records every call."""

    def __init__(
        self, name: str, hits: Sequence[str] = (), reader: InMemoryPassageReader | None = None
    ) -> None:
        self.name = name
        self._ids = [PassageId(h) for h in hits]
        self._reader = reader
        self.calls: list[tuple[str, SearchScope, int]] = []

    def retrieve(self, query: str, scope: SearchScope, limit: int) -> Sequence[RetrievalHit]:
        self.calls.append((query, scope, limit))
        ids = self._ids
        if self._reader is not None:
            ids = [p.id for p in self._reader.get_many(ids) if scope.admits(p.ticker, p.fiscal_year, p.item)]
        return [
            RetrievalHit(
                pid, float(len(ids) - rank), {self.name: SourceRank(rank + 1, float(len(ids) - rank))}
            )
            for rank, pid in enumerate(ids[:limit])
        ]


class InMemoryKeywordRetriever:
    """Scores passages by stemmed term overlap: a faithful-enough fake of BM25 for contract tests."""

    name = "keyword"

    def __init__(self, reader: InMemoryPassageReader) -> None:
        self._reader = reader

    def retrieve(self, query: str, scope: SearchScope, limit: int) -> Sequence[RetrievalHit]:
        terms = set(tokenize(query))
        scored = [
            (len(terms & set(tokenize(p.text))), p.id)
            for p in self._reader.all()
            if scope.admits(p.ticker, p.fiscal_year, p.item)
        ]
        ranked = sorted((s for s in scored if s[0] > 0), key=lambda s: (-s[0], s[1]))[:limit]
        return [RetrievalHit(pid, float(score)) for score, pid in ranked]


class SpyAnswerGenerator:
    """Cites the first sentence of the top passage, or raises the given error; records every call."""

    def __init__(self, error: Exception | None = None, name: str = "spy") -> None:
        self._error = error
        self._name = name
        self.calls: list[tuple[Question, Evidence]] = []

    def generate(self, question: Question, evidence: Evidence) -> DraftAnswer:
        self.calls.append((question, evidence))
        if self._error is not None:
            raise self._error
        top = evidence.passages[0]
        segment = AnswerSegment(
            f"Answer based on {top.company} filing text.", (Citation(top.id, top.sentences[0]),)
        )
        return DraftAnswer((segment,), generator=self._name, model="spy-model")


def unavailable(reason: str = "rate limited") -> Callable[[], AnswerGenerationUnavailableError]:
    return lambda: AnswerGenerationUnavailableError(reason)
