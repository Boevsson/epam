"""The text of a filing as the domain sees it: page-tagged lines grouped into 10-K sections."""

from dataclasses import dataclass

from filings_qa.shared_kernel.errors import InvalidValueError
from filings_qa.shared_kernel.values import ItemCode, PageRange


@dataclass(frozen=True, slots=True)
class Line:
    """One line of text and the 1-based PDF page it came from."""

    page: int
    text: str


@dataclass(frozen=True, slots=True)
class Section:
    """A contiguous run of lines belonging to one 10-K item."""

    item: ItemCode
    lines: tuple[Line, ...]

    def __post_init__(self) -> None:
        if not self.lines:
            raise InvalidValueError(f"section {self.item} has no lines")

    @property
    def pages(self) -> PageRange:
        return PageRange(self.lines[0].page, self.lines[-1].page)

    @property
    def text(self) -> str:
        return "\n".join(line.text for line in self.lines)


@dataclass(frozen=True, slots=True)
class SectionedDocument:
    """The 10-K body split into sections, plus the appended pages that were left out (exhibits)."""

    sections: tuple[Section, ...]
    excluded_pages: PageRange | None = None
