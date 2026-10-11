"""A deterministic stand-in for the sentence-transformers embedder."""

import zlib
from collections.abc import Sequence

import numpy as np
from numpy.typing import NDArray

from filings_qa.infrastructure.text_analysis import tokenize


class HashingEmbedder:
    """Bag-of-stemmed-words vectors: texts sharing words get similar vectors, with no model to load."""

    model_name = "hashing-test-embedder"
    dimension = 64

    def __init__(self) -> None:
        self.document_calls = 0

    def embed_documents(self, texts: Sequence[str]) -> NDArray[np.float32]:
        self.document_calls += 1
        if not texts:
            return np.zeros((0, self.dimension), dtype=np.float32)
        return np.stack([self._vector(text) for text in texts])

    def embed_query(self, text: str) -> NDArray[np.float32]:
        return self._vector(text)

    def _vector(self, text: str) -> NDArray[np.float32]:
        vector = np.zeros(self.dimension, dtype=np.float32)
        for token in tokenize(text):
            vector[zlib.crc32(token.encode()) % self.dimension] += 1.0
        norm = float(np.linalg.norm(vector))
        return vector / norm if norm else vector
