"""Request and response bodies of the HTTP API. Pydantic stays at the edge: these are mapped to and from
domain types in ``mapping.py`` and never passed inward."""

from pydantic import BaseModel, Field


class FiltersIn(BaseModel):
    tickers: list[str] = Field(default_factory=list, examples=[["AMD"]])
    fiscal_years: list[int] = Field(default_factory=list, examples=[[2022]])
    items: list[str] = Field(default_factory=list, description="10-K item codes, e.g. 1A, 7, 7A", examples=[["1A"]])


class QuestionIn(BaseModel):
    question: str = Field(max_length=4000, examples=["What drove AMD's revenue change in FY2022?"])
    filters: FiltersIn = Field(default_factory=FiltersIn)


class SearchIn(BaseModel):
    query: str = Field(max_length=4000, examples=["TSMC wafer supply"])
    mode: str = Field("hybrid", description="hybrid, keyword or semantic")
    limit: int = Field(10, ge=1, le=50)
    filters: FiltersIn = Field(default_factory=FiltersIn)


class PagesOut(BaseModel):
    start: int
    end: int


class RankOut(BaseModel):
    rank: int
    score: float


class RetrievalOut(BaseModel):
    fused_score: float
    ranks: dict[str, RankOut] = Field(description="Rank and raw score per retriever (bm25, dense, ...)")


class SourceOut(BaseModel):
    passage_id: str
    filing_id: str
    label: str
    company: str
    ticker: str
    fiscal_year: int
    item: str
    item_heading: str
    pages: PagesOut
    document_url: str


class EvidenceOut(SourceOut):
    text: str
    sentences: list[str]
    retrieval: RetrievalOut


class CitationOut(SourceOut):
    id: str
    quote: str


class SegmentOut(BaseModel):
    text: str
    citation_ids: list[str]


class ScopeOut(BaseModel):
    tickers: list[str]
    fiscal_years: list[int]
    items: list[str]
    source: str = Field(description="explicit, detected or none")


class MetaOut(BaseModel):
    generator: str
    model: str | None
    notice: str | None
    coverage: float
    timings_ms: dict[str, float]


class AnswerOut(BaseModel):
    question: str
    status: str = Field(description="grounded, partially_grounded, insufficient_evidence or extractive_fallback")
    segments: list[SegmentOut]
    citations: list[CitationOut]
    evidence: list[EvidenceOut]
    scope: ScopeOut
    meta: MetaOut


class SearchOut(BaseModel):
    query: str
    mode: str
    scope: ScopeOut
    hits: list[EvidenceOut]


class FilingOut(BaseModel):
    filing_id: str
    company: str
    ticker: str
    fiscal_year: int
    page_count: int
    passage_count: int
    document_url: str


class ReadyOut(BaseModel):
    status: str
    snapshot: str
    answer_generator: str
