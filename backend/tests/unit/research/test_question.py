import pytest

from filings_qa.research.domain.question import InvalidQuestionError, Question


def test_trims_whitespace() -> None:
    assert Question("  What are AMD's risks?  ").text == "What are AMD's risks?"


@pytest.mark.parametrize("text", ["", "   ", "ab", "x" * 1001])
def test_rejects_questions_that_are_too_short_or_too_long(text: str) -> None:
    with pytest.raises(InvalidQuestionError):
        Question(text)
