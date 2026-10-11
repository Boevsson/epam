from filings_qa.ingestion.domain.document import Line, Section
from filings_qa.ingestion.domain.sectionizer import sectionize
from filings_qa.shared_kernel.values import ItemCode, PageRange


def pages(*page_texts: str) -> list[Line]:
    """Lines of a document whose pages are given as newline-separated text."""
    return [Line(number, text) for number, page in enumerate(page_texts, start=1) for text in page.splitlines()]


def items_of(sections: tuple[Section, ...]) -> list[ItemCode]:
    return [section.item for section in sections]


TABLE_OF_CONTENTS = "\n".join(
    [
        "Index to the Form 10-K",
        "Item 1.",
        "Business",
        "1",
        "Item 1A.",
        "Risk Factors",
        "6",
        "Item 7.",
        "Management's Discussion and Analysis",
        "22",
        "Signatures",
        "131",
    ]
)


def test_splits_the_document_at_item_headings_and_keeps_the_heading_in_its_section() -> None:
    result = sectionize(
        pages(
            "Item 1. Business\nWe design chips.",
            "Item 1A. Risk Factors\nSupply may be constrained.",
        )
    )

    assert items_of(result.sections) == [ItemCode.BUSINESS, ItemCode.RISK_FACTORS]
    assert result.sections[1].text == "Item 1A. Risk Factors\nSupply may be constrained."
    assert result.sections[1].pages == PageRange.single(2)


def test_a_section_spans_every_page_until_the_next_heading() -> None:
    result = sectionize(pages("Item 1. Business\nintro", "more business", "Item 1A. Risk Factors\nrisk"))

    assert result.sections[0].pages == PageRange(1, 2)


def test_accepts_a_title_on_the_line_after_the_item_number() -> None:
    result = sectionize(pages("ITEM 1.\nBUSINESS\ntext", "ITEM 1A.\nRISK FACTORS\ntext"))

    assert items_of(result.sections) == [ItemCode.BUSINESS, ItemCode.RISK_FACTORS]


def test_text_before_item_1_becomes_the_cover_section() -> None:
    result = sectionize(pages("ANNUAL REPORT ON FORM 10-K\nCommission file number 1-442", "Item 1. Business\ntext"))

    assert items_of(result.sections) == [ItemCode.COVER, ItemCode.BUSINESS]
    assert result.sections[0].pages == PageRange.single(1)


def test_skips_the_table_of_contents() -> None:
    result = sectionize(
        pages(
            TABLE_OF_CONTENTS,
            "Item 1. Business\ntext",
            "Item 1A. Risk Factors\ntext",
            "Item 7. Management's Discussion and Analysis\ntext",
        )
    )

    assert items_of(result.sections) == [
        ItemCode.COVER,
        ItemCode.BUSINESS,
        ItemCode.RISK_FACTORS,
        ItemCode.MD_AND_A,
    ]
    assert result.sections[1].pages == PageRange.single(2)


def test_several_short_items_on_one_page_each_get_a_section() -> None:
    result = sectionize(
        pages(
            "Item 8. Financial Statements and Supplementary Data\nstatements",
            "Item 9. Changes in and Disagreements with Accountants\nNone.\nItem 9A. Controls and Procedures\n"
            "Controls are effective.\nItem 9B. Other Information\nNone.",
        )
    )

    assert items_of(result.sections) == [
        ItemCode.FINANCIAL_STATEMENTS,
        ItemCode.CHANGES_IN_ACCOUNTANTS,
        ItemCode.CONTROLS_AND_PROCEDURES,
        ItemCode.OTHER_INFORMATION,
    ]


def test_ignores_a_line_starting_with_an_earlier_item_reference() -> None:
    result = sectionize(
        pages(
            "Item 1. Business\nintro",
            "Item 1A. Risk Factors\nSee\nItem 1. Business—Government Regulation for details.",
        )
    )

    assert items_of(result.sections) == [ItemCode.BUSINESS, ItemCode.RISK_FACTORS]


def test_ignores_an_item_reference_whose_title_does_not_match_the_item() -> None:
    result = sectionize(
        pages(
            "Item 1. Business\nAs discussed in\nItem 7 of this report, margins grew.",
            "Item 1A. Risk Factors\nrisk",
        )
    )

    assert items_of(result.sections) == [ItemCode.BUSINESS, ItemCode.RISK_FACTORS]


def test_ignores_a_forward_reference_that_continues_a_sentence() -> None:
    result = sectionize(
        pages(
            "Item 1. Business\nFor collaboration agreements, see the\n"
            "Item 1A. Risk Factors—Collaborations section in this Form 10-K.",
            "Our people.\nITEM 1A.\nRISK FACTORS\nSupply may be constrained.",
        )
    )

    assert items_of(result.sections) == [ItemCode.BUSINESS, ItemCode.RISK_FACTORS]
    assert result.sections[1].pages == PageRange.single(2)


def test_a_short_leftover_header_line_is_not_a_sentence_that_continues() -> None:
    result = sectionize(
        pages(
            "Item 5. Market for Registrant's Common Equity\ntext",
            "Table of Contents\nItem 7.\nManagement's Discussion\ntext",
        )
    )

    assert items_of(result.sections) == [ItemCode.MARKET_FOR_EQUITY, ItemCode.MD_AND_A]


def test_a_combined_heading_starts_the_section_of_its_first_item() -> None:
    result = sectionize(
        pages(
            "Item 9C. Disclosure Regarding Foreign Jurisdictions that Prevent Inspections\nNone.",
            "PART III\nITEMS 10, 11, 12 and 13. DIRECTORS, EXECUTIVE OFFICERS AND CORPORATE GOVERNANCE;\n"
            "Incorporated by reference.\nITEM 14. PRINCIPAL ACCOUNTANT FEES AND SERVICES\nIncorporated.",
        )
    )

    assert items_of(result.sections) == [
        ItemCode.FOREIGN_JURISDICTION_INSPECTIONS,
        ItemCode.DIRECTORS_AND_GOVERNANCE,
        ItemCode.ACCOUNTANT_FEES,
    ]


def test_ignores_sub_references_such_as_item_15_a_3() -> None:
    result = sectionize(pages("Item 15. Exhibits and Financial Statement Schedules\nlist", "ITEM 15(a)(3)\nmore"))

    assert items_of(result.sections) == [ItemCode.EXHIBITS]


def test_stops_at_signatures_after_the_last_item_and_reports_excluded_exhibit_pages() -> None:
    result = sectionize(
        pages(
            TABLE_OF_CONTENTS,
            "Item 1. Business\ntext",
            "Item 16. Form 10-K Summary\nNone.\nSIGNATURES\nPursuant to the requirements",
            "EXHIBIT 10.1 PENSION PLAN",
            "more exhibit text",
        )
    )

    assert items_of(result.sections) == [ItemCode.COVER, ItemCode.BUSINESS, ItemCode.FORM_10K_SUMMARY]
    assert result.sections[-1].text == "Item 16. Form 10-K Summary\nNone."
    assert result.excluded_pages == PageRange(3, 5)


def test_without_any_headings_the_whole_document_is_one_unknown_section() -> None:
    result = sectionize(pages("just text", "more text"))

    assert items_of(result.sections) == [ItemCode.UNKNOWN]
    assert result.sections[0].pages == PageRange(1, 2)
    assert result.excluded_pages is None


def test_an_empty_document_has_no_sections() -> None:
    assert sectionize([]).sections == ()
