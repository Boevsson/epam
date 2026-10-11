import pytest

from filings_qa.evaluation.metrics import GoldenQuestion, RetrievedPassage, score_question, summarize
from filings_qa.shared_kernel.values import FilingId, PageRange

QUESTION = GoldenQuestion("q1", "Who makes AMD's wafers?", FilingId("AMD-10K-2022"), frozenset({12, 40}))


def retrieved(filing: str, start: int, end: int | None = None) -> RetrievedPassage:
    return RetrievedPassage(FilingId(filing), PageRange(start, end or start))


def test_the_first_relevant_rank_counts_only_the_right_filing_and_overlapping_pages() -> None:
    ranking = [retrieved("PFE-10K-2021", 12), retrieved("AMD-10K-2022", 3), retrieved("AMD-10K-2022", 11, 12)]

    assert score_question(QUESTION, ranking, k=10).first_relevant_rank == 3


def test_recall_is_the_share_of_evidence_pages_covered_in_the_top_k() -> None:
    ranking = [retrieved("AMD-10K-2022", 12), retrieved("AMD-10K-2022", 13), retrieved("AMD-10K-2022", 40)]

    assert score_question(QUESTION, ranking, k=2).recall == pytest.approx(0.5)
    assert score_question(QUESTION, ranking, k=3).recall == pytest.approx(1.0)


def test_nothing_relevant_scores_zero() -> None:
    score = score_question(QUESTION, [retrieved("AMD-10K-2022", 1)], k=10)

    assert score.first_relevant_rank is None
    assert score.recall == 0.0


def test_summary_averages_hit_rate_mrr_and_recall_over_questions() -> None:
    scores = [
        score_question(QUESTION, [retrieved("AMD-10K-2022", 12)], k=10),  # rank 1
        score_question(QUESTION, [retrieved("AMD-10K-2022", 1), retrieved("AMD-10K-2022", 40)], k=10),  # rank 2
        score_question(QUESTION, [retrieved("AMD-10K-2022", 1)], k=10),  # miss
    ]

    summary = summarize("hybrid", scores, latencies_ms=[10.0, 20.0, 30.0])

    assert summary.hit_at_1 == pytest.approx(1 / 3)
    assert summary.hit_at_5 == pytest.approx(2 / 3)
    assert summary.mrr == pytest.approx((1 + 0.5 + 0) / 3)
    assert summary.recall == pytest.approx((0.5 + 0.5 + 0) / 3)
    assert summary.p50_latency_ms == pytest.approx(20.0)
