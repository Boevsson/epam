import pytest

from filings_qa.ingestion.domain.chunking import Chunk, Chunker, ChunkingPolicy
from filings_qa.ingestion.domain.filing import Filing, FilingMetadata, prepare_filing
from filings_qa.shared_kernel.errors import InvalidValueError
from filings_qa.shared_kernel.values import FiscalYear, FormType, ItemCode, PageRange, Ticker

SHA = "a" * 64

PFIZER = FilingMetadata(
    company="Pfizer Inc.",
    ticker=Ticker("PFE"),
    form=FormType.TEN_K,
    fiscal_year=FiscalYear(2021),
    aliases=("Pfizer",),
)


class WordCounter:
    def count(self, text: str) -> int:
        return len(text.split())


def chunk(item: ItemCode, pages: PageRange, *sentences: str) -> Chunk:
    return Chunk(item, pages, sentences)


def test_filing_identity_comes_from_ticker_form_and_fiscal_year() -> None:
    assert PFIZER.id == "PFE-10K-2021"


def test_passages_get_stable_ids_and_ordinals_in_document_order() -> None:
    filing = Filing.from_chunks(
        PFIZER,
        source_sha256=SHA,
        page_count=10,
        chunks=[
            chunk(ItemCode.BUSINESS, PageRange.single(3), "We discover medicines."),
            chunk(ItemCode.RISK_FACTORS, PageRange(4, 5), "Pricing pressure.", "Patent expiry."),
        ],
    )

    assert [(p.id, p.ordinal, p.item) for p in filing.passages] == [
        ("PFE-10K-2021#0000", 0, ItemCode.BUSINESS),
        ("PFE-10K-2021#0001", 1, ItemCode.RISK_FACTORS),
    ]
    assert filing.passages[1].text == "Pricing pressure. Patent expiry."


def test_a_filing_without_passages_is_rejected() -> None:
    with pytest.raises(InvalidValueError, match="no passages"):
        Filing.from_chunks(PFIZER, source_sha256=SHA, page_count=10, chunks=[])


def test_a_passage_beyond_the_last_page_is_rejected() -> None:
    with pytest.raises(InvalidValueError, match="beyond page"):
        Filing.from_chunks(
            PFIZER,
            source_sha256=SHA,
            page_count=3,
            chunks=[chunk(ItemCode.BUSINESS, PageRange(2, 4), "Text.")],
        )


def test_the_source_hash_must_be_a_sha256_hex_digest() -> None:
    with pytest.raises(InvalidValueError, match="sha256"):
        Filing.from_chunks(
            PFIZER,
            source_sha256="not-a-hash",
            page_count=3,
            chunks=[chunk(ItemCode.BUSINESS, PageRange(1, 1), "Text.")],
        )


def test_index_text_prefixes_the_passage_with_company_form_year_and_item() -> None:
    filing = Filing.from_chunks(
        PFIZER,
        source_sha256=SHA,
        page_count=30,
        chunks=[chunk(ItemCode.RISK_FACTORS, PageRange.single(20), "The Company faces pricing pressure.")],
    )

    assert filing.index_text(filing.passages[0]) == (
        "Pfizer Inc. (PFE) · Form 10-K · FY2021 · Item 1A Risk Factors\nThe Company faces pricing pressure."
    )


def test_front_matter_header_names_the_section_without_an_item_number() -> None:
    assert PFIZER_FILING_HEADER_FOR_COVER == "Pfizer Inc. (PFE) · Form 10-K · FY2021 · Cover Page and Front Matter"


PFIZER_FILING_HEADER_FOR_COVER = Filing.contextual_header_for(PFIZER, ItemCode.COVER)


def test_prepare_filing_cleans_sections_and_chunks_raw_page_text() -> None:
    pages = [
        "FORM 10-K\nPfizer Inc.",
        "Item 1. Business\nWe discover medicines. We sell vaccines.",
        "Item 1A. Risk Factors\nPricing pressure may hurt margins.",
        "Item 16. Form 10-K Summary\nNone.\nSIGNATURES\nSigned by the CEO.",
        "EXHIBIT 21 SUBSIDIARIES",
    ]

    filing = prepare_filing(PFIZER, SHA, pages, Chunker(WordCounter(), ChunkingPolicy(max_tokens=50)))

    assert [p.item for p in filing.passages] == [
        ItemCode.COVER,
        ItemCode.BUSINESS,
        ItemCode.RISK_FACTORS,
        ItemCode.FORM_10K_SUMMARY,
    ]
    assert filing.passages[2].pages == PageRange.single(3)
    assert filing.page_count == 5
    assert filing.excluded_pages == PageRange(4, 5)
