"""Use case: list the filings in the live snapshot (drives the UI filters)."""

from collections.abc import Sequence

from filings_qa.research.application.ports import FilingSummary, PassageReader


class ListFilings:
    def __init__(self, passages: PassageReader) -> None:
        self._passages = passages

    def __call__(self) -> Sequence[FilingSummary]:
        return sorted(self._passages.filings(), key=lambda f: (f.company, f.fiscal_year.value))
