"""Real embedding model: downloads ~130 MB on first run, hence marked slow."""

import numpy as np
import pytest

from filings_qa.infrastructure.embeddings import SentenceTransformerEmbedder

pytestmark = pytest.mark.slow

QUERY_PROMPT = "Represent this sentence for searching relevant passages: "


@pytest.fixture(scope="module")
def embedder() -> SentenceTransformerEmbedder:
    return SentenceTransformerEmbedder("BAAI/bge-small-en-v1.5", query_prompt=QUERY_PROMPT)


def test_embeddings_are_normalized_float32_vectors_of_the_model_dimension(
    embedder: SentenceTransformerEmbedder,
) -> None:
    vectors = embedder.embed_documents(["Supply may be constrained.", "Revenue grew."])

    assert vectors.shape == (2, 384) == (2, embedder.dimension)
    assert vectors.dtype == np.float32
    assert np.allclose(np.linalg.norm(vectors, axis=1), 1.0, atol=1e-5)


def test_the_query_instruction_is_applied_to_queries_only(embedder: SentenceTransformerEmbedder) -> None:
    text = "What are the supply chain risks?"

    assert not np.allclose(embedder.embed_query(text), embedder.embed_documents([text])[0])


def test_related_texts_are_closer_than_unrelated_ones(embedder: SentenceTransformerEmbedder) -> None:
    query = embedder.embed_query("What risks does the company face from its suppliers?")
    related, unrelated = embedder.embed_documents(
        [
            "We depend on a limited number of suppliers for key components.",
            "The board met four times in 2022.",
        ]
    )

    assert float(query @ related) > float(query @ unrelated)


def test_counts_tokens_like_the_model_without_special_tokens(embedder: SentenceTransformerEmbedder) -> None:
    assert embedder.count("supply chain") == 2
    assert embedder.max_tokens == 512
