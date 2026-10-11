"""The analyst's question."""

from dataclasses import dataclass

from filings_qa.shared_kernel.errors import InvalidValueError

MIN_LENGTH = 3
MAX_LENGTH = 1000


class InvalidQuestionError(InvalidValueError):
    """The question is empty, too short or too long."""


@dataclass(frozen=True, slots=True)
class Question:
    text: str

    def __post_init__(self) -> None:
        text = self.text.strip()
        if not MIN_LENGTH <= len(text) <= MAX_LENGTH:
            raise InvalidQuestionError(f"a question must have {MIN_LENGTH}-{MAX_LENGTH} characters")
        object.__setattr__(self, "text", text)
