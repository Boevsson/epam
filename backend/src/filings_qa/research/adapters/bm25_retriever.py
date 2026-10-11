"""Keyword retrieval: BM25 (bm25s) over finance-aware tokens, filtered by scope."""

from collections.abc import Sequence

import bm25s
import numpy as np

from filings_qa.infrastructure.snapshot import BM25_DIR
from filings_qa.infrastructure.text_analysis import tokenize
from filings_qa.research.adapters.snapshot_reader import SqliteSnapshotReader
from filings_qa.research.domain.retrieval import RetrievalHit, SourceRank
from filings_qa.research.domain.scope import SearchScope


class Bm25Retriever:
    name = "bm25"

    def __init__(self, snapshot: SqliteSnapshotReader) -> None:
        self._snapshot = snapshot
        self._index = bm25s.BM25.load(str(snapshot.path / BM25_DIR))
        self._vocabulary = set(self._index.vocab_dict)

    def retrieve(self, query: str, scope: SearchScope, limit: int) -> Sequence[RetrievalHit]:
        tokens = [token for token in tokenize(query) if token in self._vocabulary]
        mask = self._snapshot.row_mask(scope)
        allowed = int(mask.sum())
        if not tokens or allowed == 0:
            return []
        rows, scores = self._index.retrieve(
            [tokens],
            k=min(limit, allowed),
            weight_mask=mask.astype(np.float32),
            show_progress=False,
            n_threads=1,
        )
        # Masked-out documents come back with score 0 when k exceeds the matches: drop them.
        ranked = [(int(row), float(score)) for row, score in zip(rows[0], scores[0], strict=True) if score > 0]
        return [
            RetrievalHit(self._snapshot.passage_id(row), score, {self.name: SourceRank(rank, score)})
            for rank, (row, score) in enumerate(ranked, start=1)
        ]
