import pytest

from filings_qa.infrastructure.text_analysis import tokenize


def test_keeps_filing_codes_and_tickers_as_single_tokens() -> None:
    assert tokenize("Form 10-K, Item 1A, COVID-19, S&P 500") == [
        "form",
        "10-k",
        "item",
        "1a",
        "covid-19",
        "s&p",
        "500",
    ]


def test_splits_plain_hyphenated_words_so_they_match_the_unhyphenated_phrase() -> None:
    assert tokenize("supply-chain") == tokenize("supply chain")


def test_numbers_match_with_or_without_thousands_separators() -> None:
    assert tokenize("$391,035 million") == tokenize("391035 million")


def test_drops_stopwords() -> None:
    assert tokenize("the risk of the company") == tokenize("risk company")


@pytest.mark.parametrize(
    ("inflected", "base"), [("risks", "risk"), ("pricing", "price"), ("Company's", "company")]
)
def test_inflections_and_possessives_reduce_to_the_same_token(inflected: str, base: str) -> None:
    assert tokenize(inflected) == tokenize(base)


def test_normalizes_unicode_before_tokenizing() -> None:
    assert tokenize("ﬁnancial\xa0results") == tokenize("financial results")
