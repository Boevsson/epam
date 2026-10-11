"""Graceful degradation as a Decorator: when the LLM is missing or failing, quote the evidence instead."""

import logging
from dataclasses import replace

from filings_qa.research.application.ports import AnswerGenerationUnavailableError, AnswerGenerator
from filings_qa.research.domain.answer import DraftAnswer, Evidence
from filings_qa.research.domain.question import Question

logger = logging.getLogger(__name__)


class FallbackAnswerGenerator:
    def __init__(self, primary: AnswerGenerator | None, fallback: AnswerGenerator) -> None:
        self._primary = primary
        self._fallback = fallback

    def generate(self, question: Question, evidence: Evidence) -> DraftAnswer:
        if self._primary is None:
            notice = "Showing the most relevant passages: no LLM is configured (set ANTHROPIC_API_KEY)."
        else:
            try:
                return self._primary.generate(question, evidence)
            except AnswerGenerationUnavailableError as error:
                logger.warning("answer generation unavailable, using fallback: %s", error)
                notice = f"Showing the most relevant passages: the LLM is unavailable ({error})."
        return replace(self._fallback.generate(question, evidence), notice=notice)
