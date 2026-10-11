"""Text embeddings: a small port shared by ingestion (documents) and retrieval (queries), and its
sentence-transformers implementation."""

from collections.abc import Sequence
from functools import cached_property
from typing import TYPE_CHECKING, Protocol

import numpy as np
from numpy.typing import NDArray

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer


class Embedder(Protocol):
    """Queries and documents are embedded separately: many retrieval models (BGE, E5, hosted APIs with
    ``input_type``) treat them asymmetrically."""

    @property
    def model_name(self) -> str: ...

    @property
    def dimension(self) -> int: ...

    def embed_documents(self, texts: Sequence[str]) -> NDArray[np.float32]:
        """One L2-normalized row per text."""
        ...

    def embed_query(self, text: str) -> NDArray[np.float32]:
        """One L2-normalized vector."""
        ...


class SentenceTransformerEmbedder:
    """Local embeddings with sentence-transformers. Also counts tokens with the model's own tokenizer, so
    the chunker can guarantee passages fit in the model's context.

    The query instruction is passed explicitly: bge-small's config defines empty prompts, so the library's
    ``encode_query`` would silently add nothing.
    """

    def __init__(self, model_name: str, *, query_prompt: str = "", batch_size: int = 32) -> None:
        self._model_name = model_name
        self._query_prompt = query_prompt
        self._batch_size = batch_size

    @cached_property
    def _model(self) -> "SentenceTransformer":
        from sentence_transformers import SentenceTransformer  # heavy import (torch), loaded on first use

        return SentenceTransformer(self._model_name, device="cpu")

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimension(self) -> int:
        dimension = self._model.get_embedding_dimension()
        if dimension is None:
            raise RuntimeError(f"{self._model_name} does not report an embedding dimension")
        return int(dimension)

    @property
    def max_tokens(self) -> int:
        length = self._model.max_seq_length
        if length is None:
            raise RuntimeError(f"{self._model_name} does not report a maximum sequence length")
        return int(length)

    def embed_documents(self, texts: Sequence[str]) -> NDArray[np.float32]:
        vectors = self._model.encode(
            list(texts), batch_size=self._batch_size, normalize_embeddings=True, convert_to_numpy=True
        )
        return np.asarray(vectors, dtype=np.float32).reshape(len(texts), self.dimension)

    def embed_query(self, text: str) -> NDArray[np.float32]:
        vector = self._model.encode(
            [text], prompt=self._query_prompt or None, normalize_embeddings=True, convert_to_numpy=True
        )
        return np.asarray(vector, dtype=np.float32).reshape(self.dimension)

    def count(self, text: str) -> int:
        """Token count without special tokens (the TokenCounter port of the chunker)."""
        return len(self._model.tokenizer(text, add_special_tokens=False)["input_ids"])
