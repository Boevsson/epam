from filings_qa.research.domain.scope import SearchScope
from filings_qa.shared_kernel.values import FiscalYear, ItemCode, Ticker


def test_an_empty_scope_admits_everything() -> None:
    assert SearchScope().admits(Ticker("AMD"), FiscalYear(2022), ItemCode.BUSINESS)


def test_each_dimension_restricts_independently() -> None:
    scope = SearchScope(tickers=frozenset({Ticker("AMD")}), fiscal_years=frozenset({FiscalYear(2022)}))

    assert scope.admits(Ticker("AMD"), FiscalYear(2022), ItemCode.RISK_FACTORS)
    assert not scope.admits(Ticker("PFE"), FiscalYear(2022), ItemCode.RISK_FACTORS)
    assert not scope.admits(Ticker("AMD"), FiscalYear(2021), ItemCode.RISK_FACTORS)


def test_item_restriction() -> None:
    scope = SearchScope(items=frozenset({ItemCode.RISK_FACTORS}))

    assert scope.admits(Ticker("AMD"), FiscalYear(2022), ItemCode.RISK_FACTORS)
    assert not scope.admits(Ticker("AMD"), FiscalYear(2022), ItemCode.MD_AND_A)
