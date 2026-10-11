from filings_qa.ingestion.domain.cleaning import clean_pages
from filings_qa.ingestion.domain.document import Line


def texts(lines: tuple[Line, ...]) -> list[str]:
    return [line.text for line in lines]


def test_lines_remember_their_one_based_page() -> None:
    lines = clean_pages(["first page", "second page"])

    assert lines == (Line(1, "first page"), Line(2, "second page"))


def test_normalizes_non_breaking_spaces_ligatures_and_whitespace_runs() -> None:
    lines = clean_pages(["Item\xa0\xa01A.\xa0\xa0Risk   Factors\n\n  ﬁnancial  results  "])

    assert texts(lines) == ["Item 1A. Risk Factors", "financial results"]


def test_removes_a_running_header_repeated_on_most_pages() -> None:
    pages = [f"Table of Contents\nbody text {n}" for n in range(1, 5)] + ["no header here"]

    assert texts(clean_pages(pages)) == [
        "body text 1",
        "body text 2",
        "body text 3",
        "body text 4",
        "no header here",
    ]


def test_removes_a_running_header_even_when_appended_exhibits_dilute_it() -> None:
    body = [f"Table of Contents\nbody text {n}" for n in range(1, 4)]
    exhibits = [f"exhibit page {n}" for n in range(1, 10)]

    assert "Table of Contents" not in texts(clean_pages(body + exhibits))


def test_keeps_a_line_that_repeats_on_only_a_few_pages() -> None:
    pages = ["Notes to Financial Statements\nnote one", "Notes to Financial Statements\nnote two"] + [
        f"other page {n}" for n in range(1, 5)
    ]

    assert "Notes to Financial Statements" in texts(clean_pages(pages))


def test_removes_page_numbers_at_the_edges_of_a_page_but_not_inside_it() -> None:
    lines = clean_pages(["Revenue was\n152\nmillion dollars\n12", "F-3\nNotes continue"])

    assert texts(lines) == ["Revenue was", "152", "million dollars", "Notes continue"]


def test_joins_words_hyphenated_across_a_line_break() -> None:
    lines = clean_pages(["contract manufac-\nturing partners", "COVID-\n19 effects"])

    assert texts(lines) == ["contract manufacturing partners", "COVID-", "19 effects"]
