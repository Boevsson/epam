"""In-memory implementations of the ingestion ports."""

from collections.abc import Mapping, Sequence

from filings_qa.ingestion.application.ports import FilingSource
from filings_qa.ingestion.domain.filing import Filing


class InMemoryCatalog:
    def __init__(self, sources: Sequence[FilingSource]) -> None:
        self._sources = list(sources)

    def sources(self) -> Sequence[FilingSource]:
        return self._sources


class InMemoryParser:
    """Returns page texts keyed by source location; raises for unknown locations like a broken PDF would."""

    def __init__(self, pages_by_location: Mapping[str, Sequence[str]]) -> None:
        self._pages = dict(pages_by_location)
        self.parsed: list[str] = []

    def page_texts(self, source: FilingSource) -> Sequence[str]:
        self.parsed.append(source.location)
        if source.location not in self._pages:
            raise ValueError(f"cannot parse {source.location}")
        return self._pages[source.location]


class InMemorySnapshotStore:
    def __init__(self) -> None:
        self.published: list[tuple[tuple[Filing, ...], str]] = []

    def current_fingerprint(self) -> str | None:
        return self.published[-1][1] if self.published else None

    def publish(self, filings: Sequence[Filing], fingerprint: str) -> str:
        self.published.append((tuple(filings), fingerprint))
        return f"v{len(self.published)}"
