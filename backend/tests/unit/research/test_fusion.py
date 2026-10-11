import pytest

from filings_qa.research.domain.fusion import ReciprocalRankFusion
from filings_qa.research.domain.retrieval import RetrievalHit, SourceRank
from filings_qa.shared_kernel.values import PassageId
from tests.builders import ids_of, ranked


class TestReciprocalRankFusion:
    def test_passage_found_by_both_retrievers_outranks_single_source_hits(self) -> None:
        fused = ReciprocalRankFusion(k=60).fuse(
            {"bm25": ranked("A", "B", "C"), "dense": ranked("D", "B", "E")}, limit=5
        )

        assert fused[0].passage_id == "B"  # 1/62 + 1/62 > 1/61
        assert set(fused[0].provenance) == {"bm25", "dense"}

    def test_score_is_the_weighted_sum_of_reciprocal_ranks(self) -> None:
        fusion = ReciprocalRankFusion(k=60, weights={"dense": 2.0})

        fused = fusion.fuse({"bm25": ranked("A", "B"), "dense": ranked("B")}, limit=2)

        scores: dict[str, float] = {hit.passage_id: hit.score for hit in fused}
        assert scores["B"] == pytest.approx(1 / 62 + 2 / 61)
        assert scores["A"] == pytest.approx(1 / 61)

    def test_ties_are_broken_deterministically_by_passage_id(self) -> None:
        fused = ReciprocalRankFusion().fuse({"bm25": ranked("B"), "dense": ranked("A")}, limit=2)

        assert ids_of(fused) == ["A", "B"]

    def test_an_empty_ranking_leaves_the_other_ranking_unchanged(self) -> None:
        fused = ReciprocalRankFusion().fuse({"bm25": [], "dense": ranked("C", "A", "B")}, limit=3)

        assert ids_of(fused) == ["C", "A", "B"]

    def test_duplicate_hits_in_one_ranking_count_once_at_their_best_rank(self) -> None:
        fused = ReciprocalRankFusion(k=60).fuse({"bm25": ranked("A", "A", "B")}, limit=2)

        assert fused[0].score == pytest.approx(1 / 61)
        assert fused[1].provenance["bm25"].rank == 2

    def test_weights_decide_between_otherwise_equal_hits(self) -> None:
        fusion = ReciprocalRankFusion(weights={"dense": 1.5})

        fused = fusion.fuse({"bm25": ranked("A"), "dense": ranked("B")}, limit=2)

        assert ids_of(fused) == ["B", "A"]

    def test_limit_truncates_the_fused_list(self) -> None:
        fused = ReciprocalRankFusion().fuse({"bm25": ranked("A", "B", "C")}, limit=2)

        assert ids_of(fused) == ["A", "B"]

    def test_provenance_keeps_each_retrievers_rank_and_raw_score(self) -> None:
        fused = ReciprocalRankFusion().fuse(
            {
                "bm25": [RetrievalHit(PassageId("A"), 12.5)],
                "dense": [RetrievalHit(PassageId("X"), 0.91), RetrievalHit(PassageId("A"), 0.84)],
            },
            limit=3,
        )

        hit = next(h for h in fused if h.passage_id == "A")
        assert hit.provenance == {
            "bm25": SourceRank(rank=1, score=12.5),
            "dense": SourceRank(rank=2, score=0.84),
        }

    def test_no_rankings_give_no_hits(self) -> None:
        assert ReciprocalRankFusion().fuse({}, limit=5) == []

    @pytest.mark.parametrize("k", [0, -1])
    def test_rejects_non_positive_k(self, k: int) -> None:
        with pytest.raises(ValueError, match="k must be"):
            ReciprocalRankFusion(k=k)

    def test_rejects_negative_weights(self) -> None:
        with pytest.raises(ValueError, match="weights must be"):
            ReciprocalRankFusion(weights={"bm25": -0.1})

    def test_rejects_non_positive_limit(self) -> None:
        with pytest.raises(ValueError, match="limit must be"):
            ReciprocalRankFusion().fuse({"bm25": ranked("A")}, limit=0)
