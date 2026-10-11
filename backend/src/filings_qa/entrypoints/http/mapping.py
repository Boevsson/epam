"""Translation between HTTP bodies and application/domain types."""

from filings_qa.entrypoints.http.schemas import (
    AnswerOut,
    CitationOut,
    EvidenceOut,
    FiltersIn,
    MetaOut,
    PagesOut,
    RankOut,
    RetrievalOut,
    ScopeOut,
    SearchOut,
    SegmentOut,
    SourceOut,
)
from filings_qa.research.application.results import AnswerResult, EvidenceHit, SearchResult
from filings_qa.research.domain.passage import Passage
from filings_qa.research.domain.scope import ResolvedScope, SearchScope
from filings_qa.shared_kernel.values import FilingId, FiscalYear, ItemCode, PageRange, Ticker

API_PREFIX = "/api/v1"


def to_scope(filters: FiltersIn) -> SearchScope:
    """Raises InvalidValueError for a malformed ticker, year or item (reported as 422)."""
    return SearchScope(
        tickers=frozenset(Ticker.parse(t) for t in filters.tickers),
        fiscal_years=frozenset(FiscalYear(y) for y in filters.fiscal_years),
        items=frozenset(ItemCode.COVER if i.upper() == "COVER" else ItemCode.parse(i) for i in filters.items),
    )


def document_url(filing_id: FilingId, pages: PageRange | None = None) -> str:
    url = f"{API_PREFIX}/filings/{filing_id}/document"
    return f"{url}#page={pages.start}" if pages else url


def _source(passage: Passage) -> SourceOut:
    return SourceOut(
        passage_id=passage.id,
        filing_id=passage.filing_id,
        label=passage.label,
        company=passage.company,
        ticker=str(passage.ticker),
        fiscal_year=passage.fiscal_year.value,
        item=passage.item.value,
        item_heading=passage.item.heading,
        pages=PagesOut(start=passage.pages.start, end=passage.pages.end),
        document_url=document_url(passage.filing_id, passage.pages),
    )


def to_evidence(hit: EvidenceHit) -> EvidenceOut:
    return EvidenceOut(
        **_source(hit.passage).model_dump(),
        text=hit.passage.text,
        sentences=list(hit.passage.sentences),
        retrieval=RetrievalOut(
            fused_score=hit.hit.score,
            ranks={name: RankOut(rank=r.rank, score=r.score) for name, r in hit.hit.provenance.items()},
        ),
    )


def to_scope_out(resolved: ResolvedScope) -> ScopeOut:
    scope = resolved.scope
    return ScopeOut(
        tickers=sorted(str(t) for t in scope.tickers),
        fiscal_years=sorted(y.value for y in scope.fiscal_years),
        items=sorted(i.value for i in scope.items),
        source=resolved.source.value,
    )


def to_answer(result: AnswerResult) -> AnswerOut:
    passages = {hit.passage.id: hit.passage for hit in result.evidence}
    citation_ids: dict[tuple[str, str], str] = {}
    citations: list[CitationOut] = []
    segments: list[SegmentOut] = []
    for segment in result.segments:
        ids = []
        for citation in segment.citations:
            key = (citation.passage_id, citation.quote)
            if key not in citation_ids:
                citation_ids[key] = f"c{len(citation_ids) + 1}"
                citations.append(
                    CitationOut(
                        **_source(passages[citation.passage_id]).model_dump(),
                        id=citation_ids[key],
                        quote=citation.quote,
                    )
                )
            ids.append(citation_ids[key])
        segments.append(SegmentOut(text=segment.text, citation_ids=ids))
    return AnswerOut(
        question=result.question,
        status=result.status.value,
        segments=segments,
        citations=citations,
        evidence=[to_evidence(hit) for hit in result.evidence],
        scope=to_scope_out(result.scope),
        meta=MetaOut(
            generator=result.generator,
            model=result.model,
            notice=result.notice,
            coverage=round(result.coverage, 3),
            timings_ms={k: round(v, 1) for k, v in result.timings_ms.items()},
        ),
    )


def to_search(result: SearchResult) -> SearchOut:
    return SearchOut(
        query=result.query,
        mode=result.mode,
        scope=to_scope_out(result.scope),
        hits=[to_evidence(hit) for hit in result.hits],
    )
