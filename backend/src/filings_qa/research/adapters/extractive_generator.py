"""Answers without an LLM: the sentence of each top passage that best matches the question, quoted.

Used when no API key is configured or the LLM is unavailable. Clearly labeled as a fallback, never passed
off as a synthesized answer.
"""

from filings_qa.infrastructure.text_analysis import tokenize
from filings_qa.research.domain.analyst_vocabulary import AnalystVocabulary
from filings_qa.research.domain.answer import AnswerSegment, Citation, DraftAnswer, Evidence
from filings_qa.research.domain.grounding import EXTRACTIVE_GENERATOR
from filings_qa.research.domain.question import Question


class ExtractiveAnswerGenerator:
    def __init__(self, max_passages: int = 3, *, vocabulary: AnalystVocabulary | None = None) -> None:
        self._max_passages = max_passages
        self._vocabulary = vocabulary

    def generate(self, question: Question, evidence: Evidence) -> DraftAnswer:
        query = self._vocabulary.expand(question.text) if self._vocabulary else question.text
        terms = set(tokenize(query))
        segments: list[AnswerSegment] = []
        for passage in evidence.passages[: self._max_passages]:
            sentences = passage.sentences
            best = max(
                range(len(sentences)), key=lambda i: (_is_prose(sentences[i]), _overlap(terms, sentences[i]), -i)
            )
            sentence = sentences[best]
            segments += [AnswerSegment(f"“{sentence}”", (Citation(passage.id, sentence),)), AnswerSegment("\n")]
        return DraftAnswer(tuple(segments), generator=EXTRACTIVE_GENERATOR)


def _overlap(terms: set[str], sentence: str) -> int:
    return len(terms & set(tokenize(sentence)))


def _is_prose(sentence: str) -> bool:
    """Flattened table rows are mostly numbers; analysts want a sentence they can read."""
    words = sentence.split()
    numeric = sum(1 for word in words if any(ch.isdigit() for ch in word))
    return bool(words) and numeric / len(words) < 0.25
