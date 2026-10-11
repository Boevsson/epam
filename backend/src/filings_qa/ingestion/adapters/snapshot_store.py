"""Builds and publishes index snapshots: SQLite passages, a BM25 index and an embedding matrix."""

import json
import sqlite3
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path

import bm25s
import numpy as np

from filings_qa.infrastructure.embeddings import Embedder
from filings_qa.infrastructure.snapshot import (
    BM25_DIR,
    FORMAT_VERSION,
    MANIFEST_FILE,
    PASSAGES_FILE,
    SCHEMA,
    VECTORS_FILE,
    SnapshotDirectory,
    SnapshotManifest,
)
from filings_qa.infrastructure.text_analysis import tokenize
from filings_qa.ingestion.domain.filing import Filing


class FileSnapshotStore:
    """SnapshotStore port: everything is written to a staging directory and only becomes visible through
    an atomic switch of the CURRENT pointer, so a failed build never affects the live snapshot."""

    def __init__(
        self,
        directory: SnapshotDirectory,
        embedder: Embedder,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._directory = directory
        self._embedder = embedder
        self._clock = clock

    def current_fingerprint(self) -> str | None:
        manifest = self._directory.read_current_manifest()
        return manifest.fingerprint if manifest else None

    def publish(self, filings: Sequence[Filing], fingerprint: str) -> str:
        now = self._clock()
        version = now.strftime("v%Y%m%dT%H%M%S%f")
        staging = self._directory.new_staging()
        try:
            index_texts = _write_passages(staging / PASSAGES_FILE, filings)
            _write_keyword_index(staging / BM25_DIR, index_texts)
            vectors = self._embedder.embed_documents(index_texts)
            np.save(staging / VECTORS_FILE, vectors.astype(np.float32))
            manifest = SnapshotManifest(
                format_version=FORMAT_VERSION,
                version=version,
                created_at=now.isoformat(),
                fingerprint=fingerprint,
                embedding_model=self._embedder.model_name,
                embedding_dimension=self._embedder.dimension,
                passage_count=len(index_texts),
                filing_ids=tuple(filing.id for filing in filings),
            )
            (staging / MANIFEST_FILE).write_text(manifest.to_json(), encoding="utf-8")
            return self._directory.publish(staging, version).name
        except BaseException:
            self._directory.discard(staging)
            raise


def _write_passages(path: Path, filings: Sequence[Filing]) -> list[str]:
    """Write filings and passages; return each passage's index text in row_id order."""
    index_texts: list[str] = []
    with sqlite3.connect(path) as db:
        db.executescript(SCHEMA)
        for filing in filings:
            meta, excluded = filing.metadata, filing.excluded_pages
            db.execute(
                "INSERT INTO filings VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    filing.id, meta.company, str(meta.ticker), str(meta.form), meta.fiscal_year.value,
                    json.dumps(list(meta.aliases)), filing.source_sha256, filing.page_count,
                    excluded.start if excluded else None, excluded.end if excluded else None,
                    len(filing.passages),
                ),
            )  # fmt: skip
            for passage in filing.passages:
                header = Filing.contextual_header_for(meta, passage.item)
                db.execute(
                    "INSERT INTO passages VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        len(index_texts), passage.id, filing.id, passage.item.value, passage.pages.start,
                        passage.pages.end, header, passage.text, json.dumps(list(passage.sentences)),
                    ),
                )  # fmt: skip
                index_texts.append(filing.index_text(passage))
    return index_texts


def _write_keyword_index(path: Path, index_texts: Sequence[str]) -> None:
    retriever = bm25s.BM25()
    retriever.index([tokenize(text) for text in index_texts], show_progress=False)
    retriever.save(str(path))
