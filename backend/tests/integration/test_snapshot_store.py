import json
import sqlite3
from datetime import UTC, datetime
from itertools import count
from pathlib import Path

import numpy as np
import pytest

from filings_qa.infrastructure.snapshot import SnapshotDirectory
from filings_qa.ingestion.adapters.snapshot_store import FileSnapshotStore
from filings_qa.ingestion.domain.chunking import Chunk
from filings_qa.ingestion.domain.filing import Filing, FilingMetadata
from filings_qa.shared_kernel.values import FiscalYear, FormType, ItemCode, PageRange, Ticker
from tests.fakes.embeddings import HashingEmbedder


def filing(ticker: str, year: int, *texts: str) -> Filing:
    metadata = FilingMetadata(f"{ticker} Inc.", Ticker(ticker), FormType.TEN_K, FiscalYear(year), (ticker,))
    chunks = [Chunk(ItemCode.RISK_FACTORS, PageRange.single(n + 1), (text,)) for n, text in enumerate(texts)]
    return Filing.from_chunks(
        metadata, source_sha256="f" * 64, page_count=10, chunks=chunks, source_name=f"{ticker}_{year}_10K.pdf"
    )


def ticking_clock() -> datetime:
    return datetime(2026, 10, 12, 12, 0, next(_seconds), tzinfo=UTC)


_seconds = count()


@pytest.fixture
def store(tmp_path: Path) -> FileSnapshotStore:
    return FileSnapshotStore(SnapshotDirectory(tmp_path / "index"), HashingEmbedder(), clock=ticking_clock)


def test_nothing_is_published_initially(store: FileSnapshotStore) -> None:
    assert store.current_fingerprint() is None


def test_publish_writes_passages_keyword_index_vectors_and_manifest(tmp_path: Path, store: FileSnapshotStore) -> None:
    filings = [
        filing("AMD", 2022, "Supply may be constrained.", "Chips are cyclical."),
        filing("PFE", 2021, "Pricing."),
    ]

    version = store.publish(filings, fingerprint="abc")

    snapshot = SnapshotDirectory(tmp_path / "index").current_path()
    assert snapshot is not None
    assert snapshot.name == version
    manifest = json.loads((snapshot / "manifest.json").read_text())
    assert manifest["fingerprint"] == "abc"
    assert manifest["passage_count"] == 3
    assert manifest["embedding_model"] == "hashing-test-embedder"
    assert np.load(snapshot / "vectors.npy").shape == (3, HashingEmbedder.dimension)
    assert (snapshot / "bm25").is_dir()
    with sqlite3.connect(snapshot / "passages.sqlite") as db:
        rows = db.execute("SELECT row_id, passage_id, item, page_start FROM passages ORDER BY row_id").fetchall()
    assert rows == [
        (0, "AMD-10K-2022#0000", "1A", 1),
        (1, "AMD-10K-2022#0001", "1A", 2),
        (2, "PFE-10K-2021#0000", "1A", 1),
    ]
    with sqlite3.connect(snapshot / "passages.sqlite") as db:
        sources = db.execute("SELECT filing_id, source_file FROM filings ORDER BY filing_id").fetchall()
    assert sources == [("AMD-10K-2022", "AMD_2022_10K.pdf"), ("PFE-10K-2021", "PFE_2021_10K.pdf")]
    assert store.current_fingerprint() == "abc"


def test_a_new_publish_becomes_current_and_keeps_the_previous_snapshot(
    tmp_path: Path, store: FileSnapshotStore
) -> None:
    first = store.publish([filing("AMD", 2022, "One.")], fingerprint="one")

    second = store.publish([filing("AMD", 2022, "Two.")], fingerprint="two")

    directory = SnapshotDirectory(tmp_path / "index")
    assert second != first
    assert directory.current_path() == tmp_path / "index" / second
    assert (tmp_path / "index" / first).is_dir()


class ExplodingEmbedder(HashingEmbedder):
    def embed_documents(self, texts: object) -> np.typing.NDArray[np.float32]:
        raise RuntimeError("model crashed")


def test_a_failed_publish_leaves_the_live_snapshot_untouched(tmp_path: Path) -> None:
    directory = SnapshotDirectory(tmp_path / "index")
    FileSnapshotStore(directory, HashingEmbedder(), clock=ticking_clock).publish([filing("AMD", 2022, "x")], "good")

    broken = FileSnapshotStore(directory, ExplodingEmbedder(), clock=ticking_clock)
    with pytest.raises(RuntimeError, match="model crashed"):
        broken.publish([filing("AMD", 2022, "y")], fingerprint="bad")

    assert broken.current_fingerprint() == "good"
    assert not [p for p in (tmp_path / "index").iterdir() if p.name.startswith(".staging")]
