"""Properties that must hold for Reciprocal Rank Fusion on any input, checked with Hypothesis."""

from hypothesis import assume, given
from hypothesis import strategies as st

from filings_qa.research.domain.fusion import ReciprocalRankFusion
from filings_qa.research.domain.retrieval import RetrievalHit
from filings_qa.shared_kernel.values import PassageId
from tests.builders import ranked, score_of

Rankings = dict[str, list[RetrievalHit]]

PASSAGE_IDS = [PassageId(f"p{i:02d}") for i in range(12)]
EVERYTHING = len(PASSAGE_IDS)

one_ranking = st.lists(st.sampled_from(PASSAGE_IDS), unique=True, max_size=8).map(lambda ids: ranked(*ids))
rankings_strategy = st.dictionaries(st.sampled_from(["bm25", "dense", "splade"]), one_ranking, max_size=3)


def union_of(rankings: Rankings) -> set[str]:
    return {hit.passage_id for hits in rankings.values() for hit in hits}


@given(rankings_strategy)
def test_fused_ids_are_exactly_the_union_of_the_inputs_without_duplicates(rankings: Rankings) -> None:
    fused = ReciprocalRankFusion().fuse(rankings, limit=EVERYTHING)

    assert [hit.passage_id for hit in fused] == list(dict.fromkeys(hit.passage_id for hit in fused))
    assert {hit.passage_id for hit in fused} == union_of(rankings)


@given(rankings_strategy)
def test_fused_scores_never_increase_down_the_list(rankings: Rankings) -> None:
    scores = [hit.score for hit in ReciprocalRankFusion().fuse(rankings, limit=EVERYTHING)]

    assert scores == sorted(scores, reverse=True)


@given(rankings_strategy, st.integers(min_value=1, max_value=20))
def test_limit_caps_the_number_of_hits(rankings: Rankings, limit: int) -> None:
    fused = ReciprocalRankFusion().fuse(rankings, limit=limit)

    assert len(fused) == min(limit, len(union_of(rankings)))


@given(rankings_strategy)
def test_result_does_not_depend_on_the_order_retrievers_are_listed(rankings: Rankings) -> None:
    fusion = ReciprocalRankFusion()
    listed_backwards = dict(reversed(list(rankings.items())))

    assert fusion.fuse(rankings, limit=EVERYTHING) == fusion.fuse(listed_backwards, limit=EVERYTHING)


@given(rankings_strategy, st.data())
def test_promoting_a_passage_in_one_ranking_never_lowers_its_fused_score(
    rankings: Rankings, data: st.DataObject
) -> None:
    promotable = [(source, position) for source, hits in rankings.items() for position in range(1, len(hits))]
    assume(promotable)
    source, position = data.draw(st.sampled_from(promotable))
    target = rankings[source][position].passage_id
    promoted_hits = list(rankings[source])
    promoted_hits[position - 1], promoted_hits[position] = (
        promoted_hits[position],
        promoted_hits[position - 1],
    )
    fusion = ReciprocalRankFusion()

    before = score_of(target, fusion.fuse(rankings, limit=EVERYTHING))
    after = score_of(target, fusion.fuse({**rankings, source: promoted_hits}, limit=EVERYTHING))

    assert after >= before
