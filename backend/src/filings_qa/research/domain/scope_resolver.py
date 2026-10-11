"""Infer which companies and fiscal years a question is about, conservatively.

10-K language is highly repetitive across companies ("we depend on suppliers..."), so searching the wrong
company's filing is the most common way to retrieve plausible but wrong evidence. Detection only uses
names, aliases and tickers of companies that are actually in the corpus, and a year only restricts the
search when a filing for it exists. The resolved scope is returned so the UI can show (and the analyst can
override) what was assumed.
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass

from filings_qa.research.domain.scope import ResolvedScope, ScopeSource, SearchScope
from filings_qa.shared_kernel.values import FiscalYear, Ticker

_YEAR = re.compile(r"\b(?:FY\s?'?(\d{2}(?:\d{2})?)|(?:fiscal\s+(?:year\s+)?)?((?:19|20)\d{2}))\b", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class CompanyProfile:
    ticker: Ticker
    name: str
    aliases: tuple[str, ...]
    fiscal_years: tuple[int, ...]


class ScopeResolver:
    def __init__(self, companies: Sequence[CompanyProfile]) -> None:
        self._companies = list(companies)
        self._patterns = [(company, _company_pattern(company)) for company in self._companies]

    def resolve(self, question: str, explicit: SearchScope) -> ResolvedScope:
        if not explicit.is_unrestricted:
            return ResolvedScope(explicit, ScopeSource.EXPLICIT)
        companies = [company for company, pattern in self._patterns if pattern.search(question)]
        candidates = companies or self._companies
        available = {year for company in candidates for year in company.fiscal_years}
        mentioned = _mentioned_years(question)
        years = frozenset(FiscalYear(year) for year in mentioned & available)
        scope = SearchScope(tickers=frozenset(company.ticker for company in companies), fiscal_years=years)
        return ResolvedScope(scope, ScopeSource.NONE if scope.is_unrestricted else ScopeSource.DETECTED)


def _company_pattern(company: CompanyProfile) -> re.Pattern[str]:
    names = {company.name, *company.aliases}
    alternatives = "|".join(re.escape(name) for name in sorted(names, key=len, reverse=True))
    by_name = rf"(?<![\w&])(?i:{alternatives})(?![\w&])"
    by_ticker = rf"(?<![\w&]){re.escape(str(company.ticker))}(?![\w&])"  # tickers are matched case-sensitively
    return re.compile(f"{by_name}|{by_ticker}")


def _mentioned_years(question: str) -> set[int]:
    years: set[int] = set()
    for short_or_long, plain in _YEAR.findall(question):
        value = short_or_long or plain
        years.add(int(value) + 2000 if len(value) == 2 else int(value))
    return years
