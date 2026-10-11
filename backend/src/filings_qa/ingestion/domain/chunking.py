"""Split a 10-K section into passages that fit the embedding model.

Policy: never cross an item boundary (one section in, its chunks out); pack whole sentences up to the
token budget; repeat trailing sentences as overlap so a fact split across chunks stays retrievable; split a
"sentence" that alone exceeds the budget (typically a flattened table) into word windows. The budget must
leave room for the contextual header added at indexing time, or the embedder silently truncates.
"""

import bisect
import re
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from typing import Protocol

from filings_qa.ingestion.domain.document import Section
from filings_qa.ingestion.domain.sentences import split_sentences
from filings_qa.shared_kernel.errors import InvalidValueError
from filings_qa.shared_kernel.values import ItemCode, PageRange

_WORD = re.compile(r"\S+")


class TokenCounter(Protocol):
    """Counts tokens the way the embedding model will (a port: the real one wraps its tokenizer)."""

    def count(self, text: str) -> int: ...


@dataclass(frozen=True, slots=True)
class ChunkingPolicy:
    max_tokens: int = 350
    overlap_tokens: int = 50

    def __post_init__(self) -> None:
        if self.max_tokens < 1 or not 0 <= self.overlap_tokens < self.max_tokens:
            raise InvalidValueError(f"invalid chunking policy: {self.max_tokens=}, {self.overlap_tokens=}")


@dataclass(frozen=True, slots=True)
class Chunk:
    item: ItemCode
    pages: PageRange
    sentences: tuple[str, ...]

    @property
    def text(self) -> str:
        return " ".join(self.sentences)


@dataclass(frozen=True, slots=True)
class _Unit:
    """A sentence (or a window of an over-long one) with its token count and page range."""

    text: str
    tokens: int
    pages: PageRange


class _PageLookup(Protocol):
    def __call__(self, start: int, end: int) -> PageRange: ...


class Chunker:
    def __init__(self, counter: TokenCounter, policy: ChunkingPolicy | None = None) -> None:
        self._counter = counter
        self._policy = policy or ChunkingPolicy()

    def chunk(self, section: Section) -> list[Chunk]:
        return self._pack(section.item, list(self._units(section)))

    def _units(self, section: Section) -> Iterator[_Unit]:
        text = " ".join(line.text for line in section.lines)
        line_starts: list[int] = []
        offset = 0
        for line in section.lines:
            line_starts.append(offset)
            offset += len(line.text) + 1
        line_pages = [line.page for line in section.lines]

        def pages(start: int, end: int) -> PageRange:
            first = line_pages[bisect.bisect_right(line_starts, start) - 1]
            last = line_pages[bisect.bisect_right(line_starts, max(start, end - 1)) - 1]
            return PageRange(first, last)

        cursor = 0
        for sentence in split_sentences(text):
            start = text.find(sentence, cursor)
            start = cursor if start < 0 else start
            cursor = start + len(sentence)
            tokens = self._counter.count(sentence)
            if tokens <= self._policy.max_tokens:
                yield _Unit(sentence, tokens, pages(start, cursor))
            else:
                yield from self._windows(sentence, start, pages)

    def _windows(self, sentence: str, base: int, pages: _PageLookup) -> Iterator[_Unit]:
        window: list[re.Match[str]] = []
        window_tokens = 0
        for word in _WORD.finditer(sentence):
            tokens = self._counter.count(word.group())
            if window and window_tokens + tokens > self._policy.max_tokens:
                yield self._window_unit(window, window_tokens, base, pages)
                window, window_tokens = [], 0
            window.append(word)
            window_tokens += tokens
        if window:
            yield self._window_unit(window, window_tokens, base, pages)

    @staticmethod
    def _window_unit(words: Sequence[re.Match[str]], tokens: int, base: int, pages: _PageLookup) -> _Unit:
        text = " ".join(word.group() for word in words)
        return _Unit(text, tokens, pages(base + words[0].start(), base + words[-1].end()))

    def _pack(self, item: ItemCode, units: Sequence[_Unit]) -> list[Chunk]:
        chunks: list[Chunk] = []
        current: list[_Unit] = []
        for unit in units:
            if current and _tokens(current) + unit.tokens > self._policy.max_tokens:
                chunks.append(_chunk(item, current))
                current = self._overlap(current)
                if _tokens(current) + unit.tokens > self._policy.max_tokens:
                    current = []
            current.append(unit)
        if current:
            chunks.append(_chunk(item, current))
        return chunks

    def _overlap(self, units: Sequence[_Unit]) -> list[_Unit]:
        tail: list[_Unit] = []
        for unit in reversed(units):
            if _tokens(tail) + unit.tokens > self._policy.overlap_tokens:
                break
            tail.insert(0, unit)
        return tail


def _tokens(units: Sequence[_Unit]) -> int:
    return sum(unit.tokens for unit in units)


def _chunk(item: ItemCode, units: Sequence[_Unit]) -> Chunk:
    return Chunk(
        item=item,
        pages=PageRange(units[0].pages.start, max(unit.pages.end for unit in units)),
        sentences=tuple(unit.text for unit in units),
    )
