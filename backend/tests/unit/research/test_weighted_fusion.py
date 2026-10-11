import pytest

from filings_qa.research.domain.fusion import WeightedScoreFusion
from filings_qa.research.domain.retrieval import RetrievalHit
from filings_qa.shared_kernel.values import PassageId
from tests.builders import ids_of


def scored(*pairs: tuple[str, float]) -> list[RetrievalHit]:
    return [RetrievalHit(PassageId(pid), score) for pid, score in pairs]


BM25 = scored(("A", 12.0), ("B", 6.0), ("C", 0.5))
DENSE = scored(("C", 0.91), ("B", 0.80), ("D", 0.79))


def test_alpha_one_follows_the_dense_ranking() -> None:
    fused = WeightedScoreFusion(alpha=1.0).fuse({"bm25": BM25, "dense": DENSE}, limit=4)

    assert ids_of(fused)[:2] == ["C", "B"]  # D (dense minimum) and A (no dense hit) tie at 0


def test_alpha_zero_follows_the_keyword_ranking() -> None:
    fused = WeightedScoreFusion(alpha=0.0).fuse({"bm25": BM25, "dense": DENSE}, limit=4)

    assert ids_of(fused)[:3] == ["A", "B", "C"]


def test_scores_are_min_max_normalized_per_retriever_before_mixing() -> None:
    fused = WeightedScoreFusion(alpha=0.5).fuse({"bm25": BM25, "dense": DENSE}, limit=4)

    scores: dict[str, float] = {hit.passage_id: hit.score for hit in fused}
    assert scores["B"] == pytest.approx(0.5 * (6.0 - 0.5) / (12.0 - 0.5) + 0.5 * (0.80 - 0.79) / (0.91 - 0.79))
    assert set(fused[0].provenance) <= {"bm25", "dense"}


@pytest.mark.parametrize("alpha", [-0.1, 1.1])
def test_rejects_alpha_outside_zero_to_one(alpha: float) -> None:
    with pytest.raises(ValueError, match="alpha"):
        WeightedScoreFusion(alpha=alpha)
