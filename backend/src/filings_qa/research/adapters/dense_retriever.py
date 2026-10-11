"""Semantic retrieval: exact cosine similarity over the snapshot's embedding matrix.

At a few thousand 384-dimensional vectors a NumPy matrix-vector product takes well under a millisecond and
returns the same results as an exact FAISS index. FAISS was dropped because faiss-cpu and torch wheels each
bundle their own OpenMP runtime, which crashes the process on macOS. An approximate index (FAISS HNSW,
Qdrant, OpenSearch) is the scaling path behind the same Retriever port.
"""

from collections.abc import Sequence

import numpy as np

from filings_qa.infrastructure.embeddings import Embedder
from filings_qa.infrastructure.snapshot import VECTORS_FILE
from filings_qa.research.adapters.snapshot_reader import SqliteSnapshotReader
from filings_qa.research.domain.retrieval import RetrievalHit, SourceRank
from filings_qa.research.domain.scope import SearchScope


class DenseRetriever:
    name = "dense"

    def __init__(self, snapshot: SqliteSnapshotReader, embedder: Embedder, *, min_similarity: float = -1.0) -> None:
        self._snapshot = snapshot
        self._embedder = embedder
        self._vectors = np.load(snapshot.path / VECTORS_FILE)
        self._min_similarity = min_similarity
        if self._vectors.shape != (snapshot.row_count, embedder.dimension):
            raise ValueError(f"vector matrix {self._vectors.shape} does not match the snapshot and embedder")

    def retrieve(self, query: str, scope: SearchScope, limit: int) -> Sequence[RetrievalHit]:
        rows = np.flatnonzero(self._snapshot.row_mask(scope))
        if rows.size == 0:
            return []
        similarities = self._vectors[rows] @ self._embedder.embed_query(query)
        k = min(limit, rows.size)
        top = np.argpartition(-similarities, k - 1)[:k]
        top = top[np.lexsort((rows[top], -similarities[top]))]  # best first, ties broken by row
        hits = [(int(rows[i]), float(similarities[i])) for i in top if similarities[i] >= self._min_similarity]
        return [
            RetrievalHit(self._snapshot.passage_id(row), score, {self.name: SourceRank(rank, score)})
            for rank, (row, score) in enumerate(hits, start=1)
        ]
