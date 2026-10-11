from pathlib import Path

import pymupdf
from filings_qa.ingestion.adapters.pymupdf_parser import PyMuPdfParser

from filings_qa.ingestion.application.ports import FilingSource
from filings_qa.ingestion.domain.filing import FilingMetadata
from filings_qa.shared_kernel.values import FiscalYear, FormType, Ticker


def make_pdf(path: Path, pages: list[str]) -> Path:
    document = pymupdf.open()
    for text in pages:
        document.new_page().insert_text((72, 72), text)
    document.save(path)
    return path


def test_returns_the_text_of_every_page_in_order(tmp_path: Path) -> None:
    pdf = make_pdf(tmp_path / "filing.pdf", ["Item 1. Business", "Item 1A. Risk Factors", "SIGNATURES"])
    metadata = FilingMetadata("Acme Corp.", Ticker("ACME"), FormType.TEN_K, FiscalYear(2022))

    pages = PyMuPdfParser().page_texts(FilingSource(metadata, str(pdf), "0" * 64))

    assert [page.strip() for page in pages] == ["Item 1. Business", "Item 1A. Risk Factors", "SIGNATURES"]
