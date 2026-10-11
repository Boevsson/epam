"""The Filing aggregate: one 10-K and its passages, indexed together or not at all."""

import re
from collections.abc import Sequence
from dataclasses import dataclass

from filings_qa.ingestion.domain.chunking import Chunk, Chunker
from filings_qa.ingestion.domain.cleaning import clean_pages
from filings_qa.ingestion.domain.sectionizer import sectionize
from filings_qa.shared_kernel.errors import InvalidValueError
from filings_qa.shared_kernel.values import (
    FilingId,
    FiscalYear,
    FormType,
    ItemCode,
    PageRange,
    PassageId,
    Ticker,
    make_filing_id,
    make_passage_id,
)

_SHA256 = re.compile(r"[0-9a-f]{64}")
_NOT_NUMBERED = (ItemCode.COVER, ItemCode.UNKNOWN)


@dataclass(frozen=True, slots=True)
class FilingMetadata:
    """What the corpus manifest states about a filing (trusted over anything guessed from PDF text)."""

    company: str
    ticker: Ticker
    form: FormType
    fiscal_year: FiscalYear
    aliases: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.company.strip():
            raise InvalidValueError("company name is empty")

    @property
    def id(self) -> FilingId:
        return make_filing_id(self.ticker, self.form, self.fiscal_year)


@dataclass(frozen=True, slots=True)
class Passage:
    """A retrievable span of one item, with the pages it came from. Sentences are the citable units."""

    id: PassageId
    ordinal: int
    item: ItemCode
    pages: PageRange
    sentences: tuple[str, ...]

    @property
    def text(self) -> str:
        return " ".join(self.sentences)


@dataclass(frozen=True, slots=True)
class Filing:
    """Aggregate root. Invariants: at least one passage; ordinals 0..n-1 in document order; ids derived
    from the filing id; every passage within the PDF's pages; the source identified by its SHA-256."""

    metadata: FilingMetadata
    source_sha256: str
    page_count: int
    passages: tuple[Passage, ...]
    excluded_pages: PageRange | None = None

    def __post_init__(self) -> None:
        if not _SHA256.fullmatch(self.source_sha256):
            raise InvalidValueError(f"source_sha256 is not a sha256 hex digest: {self.source_sha256!r}")
        if not self.passages:
            raise InvalidValueError(f"filing {self.id} has no passages")
        for ordinal, passage in enumerate(self.passages):
            if passage.ordinal != ordinal or passage.id != make_passage_id(self.id, ordinal):
                raise InvalidValueError(f"passage {passage.id} is out of order in filing {self.id}")
            if passage.pages.end > self.page_count:
                raise InvalidValueError(f"passage {passage.id} reaches beyond page {self.page_count}")

    @classmethod
    def from_chunks(
        cls,
        metadata: FilingMetadata,
        *,
        source_sha256: str,
        page_count: int,
        chunks: Sequence[Chunk],
        excluded_pages: PageRange | None = None,
    ) -> "Filing":
        passages = tuple(
            Passage(make_passage_id(metadata.id, ordinal), ordinal, chunk.item, chunk.pages, chunk.sentences)
            for ordinal, chunk in enumerate(chunks)
        )
        return cls(metadata, source_sha256, page_count, passages, excluded_pages)

    @property
    def id(self) -> FilingId:
        return self.metadata.id

    @staticmethod
    def contextual_header_for(metadata: FilingMetadata, item: ItemCode) -> str:
        section = item.heading if item in _NOT_NUMBERED else f"Item {item.value} {item.heading}"
        parts = (
            f"{metadata.company} ({metadata.ticker})",
            f"Form {metadata.form}",
            str(metadata.fiscal_year),
            section,
        )
        return " · ".join(parts)

    def index_text(self, passage: Passage) -> str:
        """The text that gets indexed: the passage prefixed with its context, so that "the Company" in an
        Apple risk factor is distinguishable from the same words in a Microsoft one."""
        return f"{self.contextual_header_for(self.metadata, passage.item)}\n{passage.text}"


def prepare_filing(
    metadata: FilingMetadata, source_sha256: str, page_texts: Sequence[str], chunker: Chunker
) -> Filing:
    """The pure ingestion pipeline: raw page text -> clean lines -> 10-K sections -> passages -> Filing."""
    document = sectionize(clean_pages(page_texts))
    chunks = [chunk for section in document.sections for chunk in chunker.chunk(section)]
    return Filing.from_chunks(
        metadata,
        source_sha256=source_sha256,
        page_count=len(page_texts),
        chunks=chunks,
        excluded_pages=document.excluded_pages,
    )
