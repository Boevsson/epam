"""Answers without an LLM: the sentence of each top passage that best matches the question, quoted.

Used when no API key is configured or the LLM is unavailable. Clearly labeled as a fallback, never passed
off as a synthesized answer.
"""

from filings_qa.infrastructure.text_analysis import tokenize
from filings_qa.research.domain.answer import AnswerSegment, Citation, DraftAnswer, Evidence
from filings_qa.research.domain.grounding import EXTRACTIVE_GENERATOR
from filings_qa.research.domain.question import Question


class ExtractiveAnswerGenerator:
    def __init__(self, max_passages: int = 3) -> None:
        self._max_passages = max_passages

    def generate(self, question: Question, evidence: Evidence) -> DraftAnswer:
        terms = set(tokenize(question.text))
        segments = []
        for passage in evidence.passages[: self._max_passages]:
            best = max(
                range(len(passage.sentences)),
                key=lambda i: (len(terms & set(tokenize(passage.sentences[i]))), -i),
            )
            sentence = passage.sentences[best]
            segments.append(AnswerSegment(f"“{sentence}”\n", (Citation(passage.id, sentence),)))
        return DraftAnswer(tuple(segments), generator=EXTRACTIVE_GENERATOR)
