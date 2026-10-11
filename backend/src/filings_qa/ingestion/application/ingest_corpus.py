"""Use case: turn the corpus of 10-K PDFs into a published, searchable snapshot."""

import hashlib
import json
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass

from filings_qa.ingestion.application.ports import CorpusCatalog, DocumentParser, FilingSource, SnapshotStore
from filings_qa.ingestion.domain.chunking import Chunker
from filings_qa.ingestion.domain.filing import Filing, prepare_filing
from filings_qa.shared_kernel.errors import DomainError
from filings_qa.shared_kernel.values import FilingId, ItemCode, PageRange


class EmptyCorpusError(DomainError):
    """The corpus manifest lists no filings."""


class DuplicateFilingError(DomainError):
    """Two sources describe the same filing (same ticker, form and fiscal year)."""


@dataclass(frozen=True, slots=True)
class FilingReport:
    filing_id: FilingId
    page_count: int
    excluded_pages: PageRange | None
    passage_count: int
    items: tuple[ItemCode, ...]

    @classmethod
    def of(cls, filing: Filing) -> "FilingReport":
        items = tuple(dict.fromkeys(passage.item for passage in filing.passages))
        return cls(filing.id, filing.page_count, filing.excluded_pages, len(filing.passages), items)


@dataclass(frozen=True, slots=True)
class IngestReport:
    snapshot_version: str | None
    skipped: bool
    filings: tuple[FilingReport, ...] = ()


class IngestCorpus:
    """Parse, clean, sectionize and chunk every filing, then publish them together as one snapshot.

    Idempotent: when the corpus fingerprint (PDF hashes, manifest metadata, pipeline settings) matches the
    live snapshot, nothing is rebuilt. All-or-nothing: one unparseable filing aborts before publishing.
    """

    def __init__(
        self,
        catalog: CorpusCatalog,
        parser: DocumentParser,
        chunker: Chunker,
        store: SnapshotStore,
        *,
        pipeline_signature: str,
    ) -> None:
        self._catalog = catalog
        self._parser = parser
        self._chunker = chunker
        self._store = store
        self._pipeline_signature = pipeline_signature

    def __call__(self, *, force: bool = False) -> IngestReport:
        sources = list(self._catalog.sources())
        if not sources:
            raise EmptyCorpusError("the corpus manifest lists no filings")
        _reject_duplicates(sources)

        fingerprint = _fingerprint(self._pipeline_signature, sources)
        if not force and self._store.current_fingerprint() == fingerprint:
            return IngestReport(snapshot_version=None, skipped=True)

        filings = [
            prepare_filing(source.metadata, source.sha256, self._parser.page_texts(source), self._chunker)
            for source in sources
        ]
        version = self._store.publish(filings, fingerprint)
        return IngestReport(version, skipped=False, filings=tuple(FilingReport.of(f) for f in filings))


def _reject_duplicates(sources: Sequence[FilingSource]) -> None:
    duplicates = [fid for fid, n in Counter(s.metadata.id for s in sources).items() if n > 1]
    if duplicates:
        raise DuplicateFilingError(f"more than one source for {', '.join(duplicates)}")


def _fingerprint(pipeline_signature: str, sources: Sequence[FilingSource]) -> str:
    described = [
        [s.metadata.id, s.sha256, s.metadata.company, list(s.metadata.aliases)]
        for s in sorted(sources, key=lambda s: s.metadata.id)
    ]
    payload = json.dumps([pipeline_signature, described], sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()
