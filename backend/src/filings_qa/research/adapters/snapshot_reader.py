"""Reads the live index snapshot: the PassageReader port plus the row filters retrievers need.

The snapshot is immutable, so everything small is loaded into memory once; reads are then lock-free and
safe from many request threads.
"""

import json
import sqlite3
from collections.abc import Sequence
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from filings_qa.infrastructure.snapshot import (
    FORMAT_VERSION,
    MANIFEST_FILE,
    PASSAGES_FILE,
    SnapshotDirectory,
    SnapshotManifest,
)
from filings_qa.research.application.ports import FilingSummary
from filings_qa.research.domain.passage import Passage
from filings_qa.research.domain.scope import SearchScope
from filings_qa.shared_kernel.values import FilingId, FiscalYear, ItemCode, PageRange, PassageId, Ticker


class SnapshotUnavailableError(Exception):
    """No snapshot has been published yet."""


class SnapshotIncompatibleError(Exception):
    """The snapshot was built with a different embedding model or format than the service expects."""


class SqliteSnapshotReader:
    def __init__(self, path: Path, manifest: SnapshotManifest) -> None:
        self.path = path
        self.manifest = manifest
        with sqlite3.connect(f"file:{path / PASSAGES_FILE}?mode=ro", uri=True) as db:
            filings = db.execute(
                "SELECT filing_id, company, ticker, fiscal_year, aliases, page_count, passage_count FROM filings"
            ).fetchall()
            rows = db.execute(
                "SELECT p.passage_id, p.filing_id, p.item, p.page_start, p.page_end, p.sentences"
                " FROM passages p ORDER BY p.row_id"
            ).fetchall()
        self._filings = [
            FilingSummary(
                FilingId(fid), company, Ticker(ticker), FiscalYear(year), tuple(json.loads(aliases)), pages, n
            )
            for fid, company, ticker, year, aliases, pages, n in filings
        ]
        by_filing = {f.filing_id: f for f in self._filings}
        self._passages: list[Passage] = []
        for passage_id, filing_id, item, start, end, sentences in rows:
            filing = by_filing[FilingId(filing_id)]
            self._passages.append(
                Passage(
                    PassageId(passage_id), filing.filing_id, filing.company, filing.ticker, filing.fiscal_year,
                    ItemCode(item), PageRange(start, end), tuple(json.loads(sentences)),
                )
            )  # fmt: skip
        self._by_id = {passage.id: passage for passage in self._passages}
        self._tickers = np.array([str(p.ticker) for p in self._passages])
        self._years = np.array([p.fiscal_year.value for p in self._passages])
        self._items = np.array([p.item.value for p in self._passages])

    @classmethod
    def open(cls, path: Path, *, expected_embedding_model: str) -> "SqliteSnapshotReader":
        manifest = SnapshotManifest.from_json((path / MANIFEST_FILE).read_text(encoding="utf-8"))
        if manifest.format_version != FORMAT_VERSION:
            raise SnapshotIncompatibleError(
                f"snapshot format {manifest.format_version} != {FORMAT_VERSION}; re-run ingestion"
            )
        if manifest.embedding_model != expected_embedding_model:
            raise SnapshotIncompatibleError(
                f"snapshot vectors come from {manifest.embedding_model!r} but the service embeds queries with "
                f"{expected_embedding_model!r}; re-run ingestion"
            )
        return cls(path, manifest)

    @classmethod
    def open_current(cls, index_dir: Path, *, expected_embedding_model: str) -> "SqliteSnapshotReader":
        current = SnapshotDirectory(index_dir).current_path()
        if current is None:
            raise SnapshotUnavailableError(f"no index snapshot in {index_dir}; run `filings-qa ingest` first")
        return cls.open(current, expected_embedding_model=expected_embedding_model)

    # PassageReader port
    def get_many(self, ids: Sequence[PassageId]) -> list[Passage]:
        return [self._by_id[passage_id] for passage_id in ids if passage_id in self._by_id]

    def filings(self) -> Sequence[FilingSummary]:
        return list(self._filings)

    # Helpers for retrievers: row i of every index is passage i
    def passage_ids(self) -> list[PassageId]:
        return [passage.id for passage in self._passages]

    def passage_id(self, row: int) -> PassageId:
        return self._passages[row].id

    @property
    def row_count(self) -> int:
        return len(self._passages)

    def row_mask(self, scope: SearchScope) -> NDArray[np.bool_]:
        mask = np.ones(self.row_count, dtype=bool)
        if scope.tickers:
            mask &= np.isin(self._tickers, [str(t) for t in scope.tickers])
        if scope.fiscal_years:
            mask &= np.isin(self._years, [y.value for y in scope.fiscal_years])
        if scope.items:
            mask &= np.isin(self._items, [i.value for i in scope.items])
        return mask
