"""Ports of the Ingestion context: what the use case needs from the outside world."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from filings_qa.ingestion.domain.filing import Filing, FilingMetadata


@dataclass(frozen=True, slots=True)
class FilingSource:
    """A filing to ingest: what the manifest says about it, where its PDF is, and the PDF's SHA-256."""

    metadata: FilingMetadata
    location: str
    sha256: str


class CorpusCatalog(Protocol):
    def sources(self) -> Sequence[FilingSource]: ...


class DocumentParser(Protocol):
    def page_texts(self, source: FilingSource) -> Sequence[str]:
        """The raw text of every page, in order."""
        ...


class SnapshotStore(Protocol):
    def current_fingerprint(self) -> str | None:
        """Fingerprint of the corpus behind the live snapshot, or None if nothing is published yet."""
        ...

    def publish(self, filings: Sequence[Filing], fingerprint: str) -> str:
        """Build indexes for all filings and atomically make them the live snapshot. Returns its version."""
        ...
