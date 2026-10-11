"""Runs every retriever configuration over the golden set and reports a comparison table."""

import time
from collections.abc import Mapping, Sequence

from filings_qa.evaluation.metrics import GoldenQuestion, RetrievedPassage, Summary, score_question, summarize
from filings_qa.research.application.ports import PassageReader, Retriever
from filings_qa.research.application.scoping import resolve_scope
from filings_qa.research.domain.scope import SearchScope


def evaluate(
    configurations: Mapping[str, tuple[Retriever, bool]],
    questions: Sequence[GoldenQuestion],
    passages: PassageReader,
    *,
    k: int = 10,
) -> list[Summary]:
    """`configurations` maps a name to (retriever, use_scope_detection)."""
    summaries = []
    for name, (retriever, detect_scope) in configurations.items():
        scores, latencies = [], []
        for question in questions:
            scope = resolve_scope(passages, question.question, SearchScope()).scope if detect_scope else SearchScope()
            started = time.perf_counter()
            hits = retriever.retrieve(question.question, scope, k)
            latencies.append((time.perf_counter() - started) * 1000)
            ranking = [RetrievedPassage(p.filing_id, p.pages) for p in passages.get_many([h.passage_id for h in hits])]
            scores.append(score_question(question, ranking, k=k))
        summaries.append(summarize(name, scores, latencies_ms=latencies))
    return summaries


def markdown_table(summaries: Sequence[Summary], *, k: int) -> str:
    lines = [
        f"| Configuration | Hit@1 | Hit@5 | Hit@{k} | MRR@{k} | Recall@{k} | p50 latency |",
        "|---|---|---|---|---|---|---|",
    ]
    lines += [
        f"| {s.name} | {s.hit_at_1:.2f} | {s.hit_at_5:.2f} | {s.hit_at_k:.2f} | {s.mrr:.2f} | {s.recall:.2f} "
        f"| {s.p50_latency_ms:.0f} ms |"
        for s in summaries
    ]
    return "\n".join(lines)
