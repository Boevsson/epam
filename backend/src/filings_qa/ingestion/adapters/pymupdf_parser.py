"""PDF text extraction with PyMuPDF (AGPL-3.0 or commercial license; swappable behind DocumentParser)."""

from collections.abc import Sequence

import pymupdf

from filings_qa.ingestion.application.ports import FilingSource


class PyMuPdfParser:
    def page_texts(self, source: FilingSource) -> Sequence[str]:
        with pymupdf.open(source.location) as document:
            return [page.get_text() for page in document]
