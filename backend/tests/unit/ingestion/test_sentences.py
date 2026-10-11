import pytest

from filings_qa.ingestion.domain.sentences import split_sentences


def test_splits_on_sentence_punctuation_followed_by_a_new_sentence() -> None:
    assert split_sentences("Revenue grew. Margins fell! Why? Costs rose.") == [
        "Revenue grew.",
        "Margins fell!",
        "Why?",
        "Costs rose.",
    ]


@pytest.mark.parametrize(
    "text",
    [
        "Apple Inc. designs phones.",
        "Sales in the U.S. grew strongly.",
        "See Note No. 3 for details.",
        "Revenue was $1.2 billion in 2022.",
        "Products, e.g. vaccines, are regulated.",
        "Johnson & Johnson Corp. and Pfizer Co. compete.",
    ],
)
def test_does_not_split_after_common_abbreviations_or_inside_numbers(text: str) -> None:
    assert split_sentences(text) == [text]


def test_bullets_start_new_sentences() -> None:
    assert split_sentences("Our values: • Courage in adversity • Excellence together") == [
        "Our values:",
        "• Courage in adversity",
        "• Excellence together",
    ]


def test_collapses_whitespace_and_ignores_blank_input() -> None:
    assert split_sentences("  One   sentence.\n  Two.  ") == ["One sentence.", "Two."]
    assert split_sentences("   ") == []
