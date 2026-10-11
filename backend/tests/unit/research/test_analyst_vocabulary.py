import pytest

from filings_qa.research.domain.analyst_vocabulary import AnalystVocabulary

vocabulary = AnalystVocabulary.default()


@pytest.mark.parametrize(
    ("question", "filing_terms"),
    [
        ("What is PepsiCo's FY2021 capex?", "purchases of property, plant and equipment"),
        ("What was the capital expenditure amount?", "purchases of property, plant and equipment"),
        ("Does AMD have a healthy quick ratio?", "current liabilities"),
        ("What is the unadjusted EBITDA margin?", "depreciation and amortization"),
        ("Did Pfizer grow its PPNE?", "property, plant and equipment"),
        ("How did the effective tax rate change?", "provision for income taxes"),
        ("Did AMD report customer concentration?", "significant customers"),
    ],
)
def test_appends_the_wording_filings_use_for_analyst_metrics(question: str, filing_terms: str) -> None:
    expanded = vocabulary.expand(question)

    assert expanded.startswith(question)
    assert filing_terms in expanded


def test_matching_is_case_insensitive_and_on_whole_words() -> None:
    assert "operating income" in vocabulary.expand("What drove OPERATING MARGIN change?")
    assert vocabulary.expand("What is the recapexed amount?") == "What is the recapexed amount?"


def test_questions_without_analyst_jargon_are_left_alone() -> None:
    assert vocabulary.expand("Who are Boeing's primary customers?") == "Who are Boeing's primary customers?"


def test_each_expansion_is_added_once_even_if_matched_twice() -> None:
    expanded = vocabulary.expand("Capex vs capital expenditures?")

    assert expanded.count("purchases of property, plant and equipment") == 1
