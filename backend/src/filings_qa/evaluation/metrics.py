"""Retrieval metrics at passage level: a passage is relevant when it comes from the expected filing and its
page range overlaps an evidence page."""

import statistics
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from filings_qa.shared_kernel.values import FilingId, PageRange


@dataclass(frozen=True, slots=True)
class GoldenQuestion:
    id: str
    question: str
    filing_id: FilingId
    pages: frozenset[int]  # 1-based evidence pages


@dataclass(frozen=True, slots=True)
class RetrievedPassage:
    filing_id: FilingId
    pages: PageRange


@dataclass(frozen=True, slots=True)
class QuestionScore:
    question_id: str
    first_relevant_rank: int | None  # 1-based, within the top k
    recall: float  # share of evidence pages covered by the top k


@dataclass(frozen=True, slots=True)
class Summary:
    name: str
    questions: int
    hit_at_1: float
    hit_at_5: float
    hit_at_k: float
    mrr: float
    recall: float
    p50_latency_ms: float


def score_question(question: GoldenQuestion, ranking: Sequence[RetrievedPassage], *, k: int) -> QuestionScore:
    top = ranking[:k]
    first = next((rank for rank, p in enumerate(top, start=1) if _covers(p, question, question.pages)), None)
    covered = {page for page in question.pages if any(_covers(p, question, {page}) for p in top)}
    recall = len(covered) / len(question.pages) if question.pages else 0.0
    return QuestionScore(question.id, first, recall)


def _covers(passage: RetrievedPassage, question: GoldenQuestion, pages: Iterable[int]) -> bool:
    return passage.filing_id == question.filing_id and any(passage.pages.start <= p <= passage.pages.end for p in pages)


def summarize(name: str, scores: Sequence[QuestionScore], *, latencies_ms: Sequence[float]) -> Summary:
    n = len(scores) or 1

    def hit_within(limit: int) -> float:
        return sum(1 for s in scores if s.first_relevant_rank is not None and s.first_relevant_rank <= limit) / n

    return Summary(
        name=name,
        questions=len(scores),
        hit_at_1=hit_within(1),
        hit_at_5=hit_within(5),
        hit_at_k=sum(1 for s in scores if s.first_relevant_rank is not None) / n,
        mrr=sum(1 / s.first_relevant_rank for s in scores if s.first_relevant_rank) / n,
        recall=sum(s.recall for s in scores) / n,
        p50_latency_ms=statistics.median(latencies_ms) if latencies_ms else 0.0,
    )
