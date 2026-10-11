import pytest

from filings_qa.research.domain.scope import ScopeSource, SearchScope
from filings_qa.research.domain.scope_resolver import CompanyProfile, ScopeResolver
from filings_qa.shared_kernel.values import FiscalYear, ItemCode, Ticker

CORPUS = [
    CompanyProfile(Ticker("AMD"), "Advanced Micro Devices, Inc.", ("AMD", "Advanced Micro Devices"), (2022,)),
    CompanyProfile(Ticker("AXP"), "American Express Company", ("American Express", "AmEx", "AMEX"), (2022,)),
    CompanyProfile(Ticker("PEP"), "PepsiCo, Inc.", ("PepsiCo", "Pepsi"), (2021, 2022)),
    CompanyProfile(Ticker("JNJ"), "Johnson & Johnson", ("Johnson & Johnson", "J&J", "JnJ"), (2022,)),
    CompanyProfile(Ticker("PFE"), "Pfizer Inc.", ("Pfizer",), (2021,)),
]
resolver = ScopeResolver(CORPUS)


def tickers(*symbols: str) -> frozenset[Ticker]:
    return frozenset(Ticker(s) for s in symbols)


def years(*values: int) -> frozenset[FiscalYear]:
    return frozenset(FiscalYear(v) for v in values)


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("What drove revenue change as of the FY22 for AMD?", tickers("AMD")),
        ("Does AMEX have an improving operating margin profile?", tickers("AXP")),
        ("Which debt securities are registered under American Express' name?", tickers("AXP")),
        ("What are the geographies that Pepsico primarily operates in?", tickers("PEP")),
        ("Roughly how many times has JnJ sold its inventory?", tickers("JNJ")),
        ("Compare Pfizer's and J&J's gross margin.", tickers("PFE", "JNJ")),
    ],
)
def test_detects_companies_by_name_alias_ticker_and_possessive(
    question: str, expected: frozenset[Ticker]
) -> None:
    resolved = resolver.resolve(question, SearchScope())

    assert resolved.scope.tickers == expected
    assert resolved.source is ScopeSource.DETECTED


def test_ignores_words_that_only_look_like_aliases() -> None:
    assert resolver.resolve("How do pepsin enzymes work?", SearchScope()).scope.tickers == frozenset()


def test_detects_fiscal_years_in_common_notations_limited_to_filings_that_exist() -> None:
    resolved = resolver.resolve("How did PepsiCo's capex change between FY2021 and FY22?", SearchScope())

    assert resolved.scope.fiscal_years == years(2021, 2022)


def test_a_year_without_a_matching_filing_does_not_restrict_the_search() -> None:
    resolved = resolver.resolve("What increased Pfizer's net income in 2019?", SearchScope())

    assert resolved.scope.tickers == tickers("PFE")
    assert resolved.scope.fiscal_years == frozenset()


def test_explicit_filters_win_over_detection() -> None:
    explicit = SearchScope(tickers=tickers("JNJ"), items=frozenset({ItemCode.RISK_FACTORS}))

    resolved = resolver.resolve("What are Pfizer's risk factors?", explicit)

    assert resolved.scope == SearchScope(tickers=tickers("JNJ"), items=frozenset({ItemCode.RISK_FACTORS}))
    assert resolved.source is ScopeSource.EXPLICIT


def test_a_question_without_any_scope_searches_everything() -> None:
    resolved = resolver.resolve("Which companies mention supply chain disruption?", SearchScope())

    assert resolved.scope == SearchScope()
    assert resolved.source is ScopeSource.NONE
