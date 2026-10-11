"""Use case: answer an analyst's question from the filings, with verifiable citations."""

import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

from filings_qa.research.application.ports import AnswerGenerator, PassageReader, Retriever
from filings_qa.research.application.results import AnswerResult, EvidenceHit
from filings_qa.research.application.scoping import resolve_scope
from filings_qa.research.domain.answer import AnswerSegment, Evidence, GroundingStatus
from filings_qa.research.domain.grounding import GroundingPolicy
from filings_qa.research.domain.question import Question
from filings_qa.research.domain.retrieval import RetrievalHit
from filings_qa.research.domain.scope import SearchScope

NO_EVIDENCE = "No passage in the indexed filings matches this question."


@dataclass(frozen=True, slots=True)
class AskQuestionCommand:
    question: str
    scope: SearchScope = field(default_factory=SearchScope)


class AskQuestion:
    def __init__(
        self,
        retriever: Retriever,
        passages: PassageReader,
        generator: AnswerGenerator,
        grounding: GroundingPolicy,
        *,
        evidence_size: int = 8,
        clock: Callable[[], float] = time.perf_counter,
    ) -> None:
        self._retriever = retriever
        self._passages = passages
        self._generator = generator
        self._grounding = grounding
        self._evidence_size = evidence_size
        self._clock = clock

    def __call__(self, command: AskQuestionCommand) -> AnswerResult:
        question = Question(command.question)
        resolved = resolve_scope(self._passages, question.text, command.scope)
        started = self._clock()
        hits = self._retriever.retrieve(question.text, resolved.scope, self._evidence_size)
        evidence_hits = _with_passages(hits, self._passages)
        retrieved = self._clock()
        timings = {"retrieval": (retrieved - started) * 1000}
        if not evidence_hits:  # nothing to ground an answer in: do not ask the LLM to guess
            return AnswerResult(
                question.text, GroundingStatus.INSUFFICIENT_EVIDENCE, (AnswerSegment(NO_EVIDENCE),), 0.0, (),
                resolved, generator="none", timings_ms=timings,
            )  # fmt: skip
        evidence = Evidence(tuple(h.passage for h in evidence_hits))
        answer = self._grounding.assess(self._generator.generate(question, evidence), evidence)
        timings["generation"] = (self._clock() - retrieved) * 1000
        return AnswerResult(
            question.text, answer.status, answer.segments, answer.coverage, evidence_hits, resolved,
            answer.generator, answer.model, answer.notice, timings,
        )  # fmt: skip


def _with_passages(hits: Sequence[RetrievalHit], passages: PassageReader) -> tuple[EvidenceHit, ...]:
    by_id = {p.id: p for p in passages.get_many([h.passage_id for h in hits])}
    return tuple(EvidenceHit(by_id[h.passage_id], h) for h in hits if h.passage_id in by_id)
