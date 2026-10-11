import pytest

from filings_qa.shared_kernel.errors import InvalidValueError
from filings_qa.shared_kernel.values import FiscalYear, FormType, ItemCode, PageRange, Ticker


class TestPageRange:
    def test_accepts_a_one_based_inclusive_range(self) -> None:
        pages = PageRange(17, 18)

        assert (pages.start, pages.end) == (17, 18)

    @pytest.mark.parametrize(("start", "end"), [(0, 1), (-3, 2), (5, 4)])
    def test_rejects_start_below_one_or_end_before_start(self, start: int, end: int) -> None:
        with pytest.raises(InvalidValueError):
            PageRange(start, end)

    def test_single_page_range(self) -> None:
        assert PageRange.single(7) == PageRange(7, 7)

    @pytest.mark.parametrize(
        ("a", "b", "expected"),
        [
            (PageRange(1, 3), PageRange(3, 5), True),
            (PageRange(1, 3), PageRange(4, 5), False),
            (PageRange(4, 9), PageRange(5, 6), True),
        ],
    )
    def test_overlap_is_symmetric(self, a: PageRange, b: PageRange, expected: bool) -> None:
        assert a.overlaps(b) is expected
        assert b.overlaps(a) is expected

    def test_renders_like_a_citation(self) -> None:
        assert str(PageRange.single(18)) == "p. 18"
        assert str(PageRange(17, 18)) == "pp. 17-18"


class TestTicker:
    def test_parse_normalizes_case_and_whitespace(self) -> None:
        assert Ticker.parse(" amd ") == Ticker("AMD")

    @pytest.mark.parametrize("symbol", ["A", "PEP", "GOOGL", "BRK.B", "BF-B"])
    def test_accepts_listed_symbol_formats(self, symbol: str) -> None:
        assert str(Ticker.parse(symbol)) == symbol

    @pytest.mark.parametrize("raw", ["", "  ", "TOOLONG", "AB1", "$AMD", "amd"])
    def test_rejects_anything_but_a_canonical_symbol(self, raw: str) -> None:
        with pytest.raises(InvalidValueError):
            Ticker(raw)


class TestFiscalYear:
    def test_orders_chronologically(self) -> None:
        assert FiscalYear(2021) < FiscalYear(2022)

    @pytest.mark.parametrize("year", [1992, 2101])
    def test_rejects_years_outside_the_edgar_era(self, year: int) -> None:
        with pytest.raises(InvalidValueError):
            FiscalYear(year)

    def test_renders_as_fy_label(self) -> None:
        assert str(FiscalYear(2022)) == "FY2022"


class TestItemCode:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("1A", ItemCode.RISK_FACTORS),
            ("1a", ItemCode.RISK_FACTORS),
            ("Item 7A", ItemCode.MARKET_RISK),
            ("ITEM 7.", ItemCode.MD_AND_A),
            (" item 1 ", ItemCode.BUSINESS),
            ("Item 9C:", ItemCode.FOREIGN_JURISDICTION_INSPECTIONS),
            ("Item 16", ItemCode.FORM_10K_SUMMARY),
        ],
    )
    def test_parses_item_labels(self, raw: str, expected: ItemCode) -> None:
        assert ItemCode.parse(raw) is expected

    @pytest.mark.parametrize("raw", ["", "Item", "17", "1D", "Part II"])
    def test_rejects_labels_that_are_not_10k_items(self, raw: str) -> None:
        with pytest.raises(InvalidValueError):
            ItemCode.parse(raw)

    @pytest.mark.parametrize("item", list(ItemCode))
    def test_every_item_has_a_heading(self, item: ItemCode) -> None:
        assert item.heading

    def test_front_matter_before_item_1_has_its_own_code(self) -> None:
        assert ItemCode("COVER").heading == "Cover Page and Front Matter"

    def test_headings_use_the_official_titles(self) -> None:
        assert ItemCode.RISK_FACTORS.heading == "Risk Factors"
        assert ItemCode.MARKET_RISK.heading == "Quantitative and Qualitative Disclosures About Market Risk"


class TestFormType:
    def test_compact_form_is_used_in_identifiers(self) -> None:
        assert FormType.TEN_K.compact == "10K"
        assert FormType.TEN_K_AMENDMENT.compact == "10KA"

    def test_parses_the_label_used_in_manifests(self) -> None:
        assert FormType("10-K") is FormType.TEN_K
