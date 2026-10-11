"""Passages as the Research context reads them: text plus everything needed to cite it."""

from dataclasses import dataclass

from filings_qa.shared_kernel.values import FilingId, FiscalYear, ItemCode, PageRange, PassageId, Ticker

_NOT_NUMBERED = (ItemCode.COVER, ItemCode.UNKNOWN)


@dataclass(frozen=True, slots=True)
class Passage:
    id: PassageId
    filing_id: FilingId
    company: str
    ticker: Ticker
    fiscal_year: FiscalYear
    item: ItemCode
    pages: PageRange
    sentences: tuple[str, ...]

    @property
    def text(self) -> str:
        return " ".join(self.sentences)

    @property
    def label(self) -> str:
        """A source reference an analyst can check: ``Pfizer Inc. · 10-K FY2021 · Item 1A ... · p. 19``."""
        section = (
            self.item.heading if self.item in _NOT_NUMBERED else f"Item {self.item.value} {self.item.heading}"
        )
        return f"{self.company} · 10-K {self.fiscal_year} · {section} · {self.pages}"
