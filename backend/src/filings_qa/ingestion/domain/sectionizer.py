"""Split a 10-K into its items (Item 1 Business, Item 1A Risk Factors, ...).

Rules, each learned from real filings:

* A heading is a line starting ``Item <code>`` whose title (same line or next line) matches the item.
  This rejects references such as "Item 7 of this report".
* Table-of-contents pages are skipped: there, headings are followed by page numbers.
  Having many headings is not enough, because short items ("Item 9B. Other Information / None.")
  often share a page in the body.
* Items appear in canonical order, so a heading that does not move forward is a cross-reference.
* A heading never continues a sentence: "...see the / Item 1A. Risk Factors—... section" is a reference.
* Combined headings ("Items 10, 11, 12 and 13. Directors, ...") start the section of their first item.
* Text before the first item is the cover page and front matter (it answers real questions).
* The 10-K body ends at "SIGNATURES" after the last item; what follows is appended exhibits.
* If no heading is found, the whole document is one UNKNOWN section: ingestion never fails here.
"""

import re
from collections import Counter
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType

from filings_qa.ingestion.domain.document import Line, Section, SectionedDocument
from filings_qa.shared_kernel.errors import InvalidValueError
from filings_qa.shared_kernel.values import ItemCode, PageRange

MIN_TABLE_OF_CONTENTS_ENTRIES = 3
MIN_SENTENCE_LENGTH = 30  # shorter lines (leftover headers like "Table of Contents") are not prose

_CODE = r"(?:1[0-6]|[1-9][a-c]?)(?![a-z0-9(])"
_HEADING = re.compile(rf"items?\s+({_CODE})(?:\s*(?:,|and|&)\s*{_CODE})*\s*[.:]?\s*(.*)", re.IGNORECASE)
_CONTINUES_SENTENCE = re.compile(r"[a-z,;]$")
_ENDS_WITH_PAGE_NUMBER = re.compile(r"(?:^|[\s.])\d{1,3}$")
_PAGE_NUMBER = re.compile(r"\d{1,3}")
_SIGNATURES = re.compile(r"signatures?", re.IGNORECASE)

_CANONICAL_ORDER: tuple[ItemCode, ...] = tuple(
    item for item in ItemCode if item not in (ItemCode.COVER, ItemCode.UNKNOWN)
)
_RANK: Mapping[ItemCode, int] = MappingProxyType({item: rank for rank, item in enumerate(_CANONICAL_ORDER)})


def _first_word(text: str) -> str:
    words = text.lower().split()
    return re.sub(r"[^a-z]", "", words[0]) if words else ""


_TITLE_PREFIXES: Mapping[ItemCode, frozenset[str]] = MappingProxyType(
    {
        item: frozenset({_first_word(item.heading)[:4]})
        | ({"sele"} if item is ItemCode.SELECTED_FINANCIAL_DATA else frozenset())
        for item in _CANONICAL_ORDER
    }
)


@dataclass(frozen=True, slots=True)
class _Heading:
    index: int
    item: ItemCode
    page: int
    looks_like_contents_entry: bool


def sectionize(lines: Sequence[Line]) -> SectionedDocument:
    """Group cleaned lines into 10-K sections."""
    if not lines:
        return SectionedDocument(sections=())
    headings = _in_canonical_order(_outside_table_of_contents(list(_candidate_headings(lines))))
    if not headings:
        return SectionedDocument(sections=(Section(ItemCode.UNKNOWN, tuple(lines)),))

    end = _end_of_body(lines, after=headings[-1].index)
    sections: list[Section] = []
    if headings[0].index > 0:
        sections.append(Section(ItemCode.COVER, tuple(lines[: headings[0].index])))
    boundaries = [heading.index for heading in headings] + [end]
    for heading, start, stop in zip(headings, boundaries, boundaries[1:], strict=False):
        sections.append(Section(heading.item, tuple(lines[start:stop])))
    excluded = PageRange(lines[end].page, lines[-1].page) if end < len(lines) else None
    return SectionedDocument(sections=tuple(sections), excluded_pages=excluded)


def _candidate_headings(lines: Sequence[Line]) -> Iterator[_Heading]:
    for index, line in enumerate(lines):
        match = _HEADING.fullmatch(line.text.strip())
        if match is None or _continues_previous_line(lines, index):
            continue
        try:
            item = ItemCode.parse(match.group(1))
        except InvalidValueError:
            continue
        title_index = index if match.group(2) else index + 1
        if title_index >= len(lines):
            continue
        title = match.group(2) or lines[title_index].text
        if not any(_first_word(title).startswith(prefix) for prefix in _TITLE_PREFIXES[item]):
            continue
        after_title = lines[title_index + 1].text.strip() if title_index + 1 < len(lines) else ""
        looks_like_contents_entry = bool(
            _ENDS_WITH_PAGE_NUMBER.search(title.strip()) or _PAGE_NUMBER.fullmatch(after_title)
        )
        yield _Heading(index, item, line.page, looks_like_contents_entry)


def _continues_previous_line(lines: Sequence[Line], index: int) -> bool:
    previous = lines[index - 1] if index > 0 else None
    return (
        previous is not None
        and previous.page == lines[index].page
        and len(previous.text) >= MIN_SENTENCE_LENGTH
        and _CONTINUES_SENTENCE.search(previous.text) is not None
    )


def _outside_table_of_contents(candidates: list[_Heading]) -> list[_Heading]:
    entries_per_page = Counter(c.page for c in candidates if c.looks_like_contents_entry)
    contents_pages = {page for page, entries in entries_per_page.items() if entries >= MIN_TABLE_OF_CONTENTS_ENTRIES}
    return [c for c in candidates if c.page not in contents_pages]


def _in_canonical_order(candidates: list[_Heading]) -> list[_Heading]:
    accepted: list[_Heading] = []
    for candidate in candidates:
        if not accepted or _RANK[candidate.item] > _RANK[accepted[-1].item]:
            accepted.append(candidate)
    return accepted


def _end_of_body(lines: Sequence[Line], after: int) -> int:
    for index in range(after + 1, len(lines)):
        if _SIGNATURES.fullmatch(lines[index].text.strip()):
            return index
    return len(lines)
