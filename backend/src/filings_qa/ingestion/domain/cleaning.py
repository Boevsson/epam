"""Turn raw page text into clean, page-tagged lines.

Removes what PDF extraction adds but readers ignore: running headers and footers (such as the
"Table of Contents" link repeated on most pages of a 10-K), page numbers, odd Unicode spacing,
and words hyphenated across line breaks.
"""

import re
import unicodedata
from collections import Counter
from collections.abc import Iterable, Sequence

from filings_qa.ingestion.domain.document import Line

EDGE_LINES = 2  # running headers and footers sit within the first or last lines of a page
MIN_REPEATS = 3
# A line at the edge of at least a fifth of all pages is page furniture, not content. Not higher: appended
# exhibits can make up most of the PDF (PepsiCo: ~420 of 549 pages) and dilute the 10-K's running header.
REPEAT_RATIO = 0.2

_PAGE_NUMBER = re.compile(r"(?:page\s+)?(?:[a-z]{1,2}-)?\d{1,4}", re.IGNORECASE)
_HYPHENATED_WORD = re.compile(r"[a-z]-$")


def clean_pages(pages: Sequence[str]) -> tuple[Line, ...]:
    """Clean the text of each page (in order) and return its lines tagged with 1-based page numbers."""
    normalized = [_normalize(page) for page in pages]
    furniture = _repeated_edge_lines(normalized)
    return tuple(
        Line(number, text)
        for number, page_lines in enumerate(normalized, start=1)
        for text in _join_hyphenated(_strip_edges(page_lines, furniture))
    )


def _normalize(page: str) -> list[str]:
    text = unicodedata.normalize("NFKC", page)  # non-breaking spaces -> spaces, ligatures -> letters
    return [" ".join(raw.split()) for raw in text.splitlines() if raw.strip()]


def _repeated_edge_lines(pages: Sequence[Sequence[str]]) -> frozenset[str]:
    counts: Counter[str] = Counter()
    for lines in pages:
        counts.update(set(lines[:EDGE_LINES]) | set(lines[-EDGE_LINES:]))
    threshold = max(MIN_REPEATS, REPEAT_RATIO * len(pages))
    return frozenset(line for line, count in counts.items() if count >= threshold)


def _strip_edges(lines: Sequence[str], furniture: frozenset[str]) -> Sequence[str]:
    start, end = 0, len(lines)
    for _ in range(EDGE_LINES):
        if start < end and _is_furniture(lines[start], furniture):
            start += 1
        if start < end and _is_furniture(lines[end - 1], furniture):
            end -= 1
    return lines[start:end]


def _is_furniture(line: str, furniture: frozenset[str]) -> bool:
    return line in furniture or _PAGE_NUMBER.fullmatch(line) is not None


def _join_hyphenated(lines: Iterable[str]) -> list[str]:
    joined: list[str] = []
    for line in lines:
        if joined and _HYPHENATED_WORD.search(joined[-1]) and line[:1].islower():
            joined[-1] = joined[-1][:-1] + line
        else:
            joined.append(line)
    return joined
