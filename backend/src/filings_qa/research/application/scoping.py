"""Builds the scope resolver from the filings that are actually indexed."""

from collections.abc import Sequence

from filings_qa.research.application.ports import FilingSummary, PassageReader
from filings_qa.research.domain.scope import ResolvedScope, SearchScope
from filings_qa.research.domain.scope_resolver import CompanyProfile, ScopeResolver


def resolve_scope(passages: PassageReader, question: str, explicit: SearchScope) -> ResolvedScope:
    return ScopeResolver(company_profiles(passages.filings())).resolve(question, explicit)


def company_profiles(filings: Sequence[FilingSummary]) -> list[CompanyProfile]:
    by_ticker: dict[str, list[FilingSummary]] = {}
    for filing in filings:
        by_ticker.setdefault(str(filing.ticker), []).append(filing)
    return [
        CompanyProfile(
            ticker=group[0].ticker,
            name=group[0].company,
            aliases=tuple(dict.fromkeys(alias for f in group for alias in f.aliases)),
            fiscal_years=tuple(sorted({f.fiscal_year.value for f in group})),
        )
        for group in by_ticker.values()
    ]
