"""Which filings a question is about."""

from dataclasses import dataclass
from enum import StrEnum

from filings_qa.shared_kernel.values import FiscalYear, ItemCode, Ticker


@dataclass(frozen=True, slots=True)
class SearchScope:
    """Restricts retrieval to companies, fiscal years and items. An empty dimension means "any".

    Also a Specification: the same predicate is used by in-memory fakes and translated by adapters.
    """

    tickers: frozenset[Ticker] = frozenset()
    fiscal_years: frozenset[FiscalYear] = frozenset()
    items: frozenset[ItemCode] = frozenset()

    def admits(self, ticker: Ticker, fiscal_year: FiscalYear, item: ItemCode) -> bool:
        return (
            (not self.tickers or ticker in self.tickers)
            and (not self.fiscal_years or fiscal_year in self.fiscal_years)
            and (not self.items or item in self.items)
        )

    @property
    def is_unrestricted(self) -> bool:
        return not (self.tickers or self.fiscal_years or self.items)


class ScopeSource(StrEnum):
    EXPLICIT = "explicit"  # the analyst chose filters
    DETECTED = "detected"  # inferred from company or year mentions in the question
    NONE = "none"  # the whole corpus is searched


@dataclass(frozen=True, slots=True)
class ResolvedScope:
    scope: SearchScope
    source: ScopeSource
