from dataclasses import replace

import pytest

from filings_qa.ingestion.application.ingest_corpus import (
    DuplicateFilingError,
    EmptyCorpusError,
    IngestCorpus,
)
from filings_qa.ingestion.application.ports import FilingSource
from filings_qa.ingestion.domain.chunking import Chunker, ChunkingPolicy
from filings_qa.ingestion.domain.filing import FilingMetadata
from filings_qa.shared_kernel.values import FiscalYear, FormType, ItemCode, Ticker
from tests.fakes.ingestion import InMemoryCatalog, InMemoryParser, InMemorySnapshotStore


class WordCounter:
    def count(self, text: str) -> int:
        return len(text.split())


def source(ticker: str, year: int, sha: str = "a") -> FilingSource:
    metadata = FilingMetadata(f"{ticker} Inc.", Ticker(ticker), FormType.TEN_K, FiscalYear(year))
    return FilingSource(metadata=metadata, location=f"{ticker}_{year}.pdf", sha256=sha * 64)


PAGES = ["Cover page", "Item 1. Business\nWe sell things.", "Item 1A. Risk Factors\nThings may go wrong."]


def make_use_case(
    sources: list[FilingSource],
    store: InMemorySnapshotStore | None = None,
    parser: InMemoryParser | None = None,
    signature: str = "pipeline-v1",
) -> tuple[IngestCorpus, InMemorySnapshotStore]:
    store = store or InMemorySnapshotStore()
    parser = parser or InMemoryParser({s.location: PAGES for s in sources})
    chunker = Chunker(WordCounter(), ChunkingPolicy(max_tokens=40, overlap_tokens=5))
    return IngestCorpus(InMemoryCatalog(sources), parser, chunker, store, pipeline_signature=signature), store


def test_ingests_every_filing_into_one_published_snapshot() -> None:
    ingest, store = make_use_case([source("AMD", 2022), source("PFE", 2021)])

    report = ingest()

    assert report.snapshot_version == "v1"
    assert not report.skipped
    assert [f.filing_id for f in report.filings] == ["AMD-10K-2022", "PFE-10K-2021"]
    assert report.filings[0].items == (ItemCode.COVER, ItemCode.BUSINESS, ItemCode.RISK_FACTORS)
    assert len(store.published) == 1
    assert [f.id for f in store.published[0][0]] == ["AMD-10K-2022", "PFE-10K-2021"]
    assert [f.source_name for f in store.published[0][0]] == ["AMD_2022.pdf", "PFE_2021.pdf"]


def test_an_unchanged_corpus_is_not_ingested_again() -> None:
    ingest, store = make_use_case([source("AMD", 2022)])
    ingest()

    report = ingest()

    assert report.skipped
    assert len(store.published) == 1


def test_force_reingests_an_unchanged_corpus() -> None:
    ingest, store = make_use_case([source("AMD", 2022)])
    ingest()

    ingest(force=True)

    assert len(store.published) == 2


def test_a_changed_pdf_triggers_reingestion() -> None:
    store = InMemorySnapshotStore()
    make_use_case([source("AMD", 2022, sha="a")], store=store)[0]()

    report = make_use_case([source("AMD", 2022, sha="b")], store=store)[0]()

    assert not report.skipped


def test_a_changed_pipeline_triggers_reingestion() -> None:
    store = InMemorySnapshotStore()
    make_use_case([source("AMD", 2022)], store=store, signature="chunks-350")[0]()

    report = make_use_case([source("AMD", 2022)], store=store, signature="chunks-300")[0]()

    assert not report.skipped


def test_rejects_two_sources_for_the_same_filing() -> None:
    first = source("AMD", 2022)
    ingest, _ = make_use_case([first, replace(first, location="copy.pdf")])

    with pytest.raises(DuplicateFilingError, match="AMD-10K-2022"):
        ingest()


def test_rejects_an_empty_corpus() -> None:
    ingest, _ = make_use_case([])

    with pytest.raises(EmptyCorpusError):
        ingest()


def test_nothing_is_published_when_any_filing_fails_to_parse() -> None:
    good, broken = source("AMD", 2022), source("PFE", 2021)
    ingest, store = make_use_case([good, broken], parser=InMemoryParser({good.location: PAGES}))

    with pytest.raises(ValueError, match="cannot parse"):
        ingest()

    assert store.published == []
