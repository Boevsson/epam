import json
import os
from pathlib import Path
from typing import Any

import anthropic
import httpx2
import pytest
from anthropic.types.beta import BetaMessage

from filings_qa.research.adapters.claude_generator import (
    SYSTEM_PROMPT,
    ClaudeAnswerGenerator,
    build_request,
    to_draft_answer,
)
from filings_qa.research.adapters.extractive_generator import ExtractiveAnswerGenerator
from filings_qa.research.application.ports import AnswerGenerationUnavailableError
from filings_qa.research.domain.analyst_vocabulary import AnalystVocabulary
from filings_qa.research.domain.answer import Evidence, GroundingStatus
from filings_qa.research.domain.grounding import GroundingPolicy
from filings_qa.research.domain.question import Question
from tests.fakes.research import make_passage

FIXTURES = Path(__file__).parent.parent / "fixtures"
SUPPLY = make_passage(
    "AMD-10K-2022#0001",
    "We rely on TSMC to manufacture our wafers.",
    "Supply constraints could limit our revenue.",
    page=17,
)
PRICING = make_passage("PFE-10K-2021#0003", "Drug pricing reform could reduce our revenue.", ticker="PFE", year=2021)
EVIDENCE = Evidence((SUPPLY, PRICING))
QUESTION = Question("Who manufactures AMD's chips and what are the supply risks?")


def fixture_message(**overrides: Any) -> BetaMessage:
    data = json.loads((FIXTURES / "claude_cited_answer.json").read_text())
    data.update(overrides)
    return BetaMessage.model_validate(data)


class TestBuildRequest:
    def test_sends_each_passage_as_a_citable_search_result_and_the_question_last(self) -> None:
        request = build_request(QUESTION, EVIDENCE, model="claude-opus-5-5", effort="medium", max_tokens=8000)

        first, second, question = request["messages"][0]["content"]
        assert first == {
            "type": "search_result",
            "source": "passage:AMD-10K-2022#0001",
            "title": SUPPLY.label,
            "content": [
                {"type": "text", "text": "We rely on TSMC to manufacture our wafers."},
                {"type": "text", "text": "Supply constraints could limit our revenue."},
            ],
            "citations": {"enabled": True},
        }
        assert second["source"] == "passage:PFE-10K-2021#0003"
        assert question == {"type": "text", "text": QUESTION.text}
        assert request["system"] == SYSTEM_PROMPT
        assert request["output_config"] == {"effort": "medium"}
        assert (request["model"], request["max_tokens"]) == ("claude-opus-5-5", 8000)


class TestToDraftAnswer:
    def test_maps_text_blocks_to_segments_and_citations_to_our_passages(self) -> None:
        draft = to_draft_answer(fixture_message(), EVIDENCE)

        assert [s.text for s in draft.segments] == [
            "AMD depends on third parties to manufacture its products",
            ", and constrained supply could limit revenue",
            ". Pfizer's filing is not relevant here.",
        ]
        assert draft.segments[0].citations[0].passage_id == "AMD-10K-2022#0001"
        assert draft.segments[2].citations == ()
        assert (draft.generator, draft.model) == ("claude", "claude-opus-5-5")

    def test_quotes_are_rebuilt_from_our_sentences_so_they_match_the_passage_exactly(self) -> None:
        draft = to_draft_answer(fixture_message(), EVIDENCE)

        assert draft.segments[1].citations[0].quote == (
            "We rely on TSMC to manufacture our wafers. Supply constraints could limit our revenue."
        )
        assert GroundingPolicy().assess(draft, EVIDENCE).status is GroundingStatus.GROUNDED

    def test_a_refusal_makes_the_generator_unavailable(self) -> None:
        with pytest.raises(AnswerGenerationUnavailableError, match="declined"):
            to_draft_answer(fixture_message(stop_reason="refusal"), EVIDENCE)

    def test_a_truncated_answer_carries_a_notice(self) -> None:
        draft = to_draft_answer(fixture_message(stop_reason="max_tokens"), EVIDENCE)

        assert draft.notice is not None
        assert "cut off" in draft.notice


class TestClaudeAnswerGenerator:
    def test_calls_the_messages_api_with_server_side_refusal_fallback(self) -> None:
        calls: list[dict[str, Any]] = []

        def create(**kwargs: Any) -> BetaMessage:
            calls.append(kwargs)
            return fixture_message()

        draft = ClaudeAnswerGenerator(create, model="claude-opus-5-5", effort="medium", max_tokens=8000).generate(
            QUESTION, EVIDENCE
        )

        assert draft.generator == "claude"
        assert calls[0]["fallbacks"] == "default"
        assert calls[0]["betas"] == ["server-side-fallback-2026-07-01"]

    @pytest.mark.parametrize(
        ("error", "reason"),
        [
            (anthropic.APIConnectionError(request=httpx2.Request("POST", "https://api.anthropic.com")), "connect"),
            (anthropic.APITimeoutError(request=httpx2.Request("POST", "https://api.anthropic.com")), "timed out"),
            (
                anthropic.RateLimitError(
                    "slow down",
                    response=httpx2.Response(429, request=httpx2.Request("POST", "https://api.anthropic.com")),
                    body=None,
                ),
                "rate limited",
            ),
            (
                anthropic.AuthenticationError(
                    "bad key",
                    response=httpx2.Response(401, request=httpx2.Request("POST", "https://api.anthropic.com")),
                    body=None,
                ),
                "ANTHROPIC_API_KEY",
            ),
        ],
    )
    def test_api_failures_become_unavailable_so_the_fallback_can_answer(self, error: Exception, reason: str) -> None:
        def create(**kwargs: Any) -> BetaMessage:
            raise error

        generator = ClaudeAnswerGenerator(create, model="claude-opus-5-5", effort="medium", max_tokens=8000)

        with pytest.raises(AnswerGenerationUnavailableError, match=reason):
            generator.generate(QUESTION, EVIDENCE)


class TestExtractiveAnswerGenerator:
    def test_quotes_the_best_matching_sentence_of_each_top_passage(self) -> None:
        draft = ExtractiveAnswerGenerator().generate(Question("What could limit AMD's revenue?"), EVIDENCE)

        assert draft.generator == "extractive"
        assert [c.quote for s in draft.segments for c in s.citations] == [
            "Supply constraints could limit our revenue.",
            "Drug pricing reform could reduce our revenue.",
        ]
        assert GroundingPolicy().assess(draft, EVIDENCE).status is GroundingStatus.EXTRACTIVE_FALLBACK

    def test_prefers_a_prose_sentence_over_a_flattened_table_row(self) -> None:
        passage = make_passage(
            "BA-10K-2022#0010",
            "Revenue customers U.S. 3,042 1,681 513 Total customers 13,567 9,905 8,711 customers 25,750 19,391",
            "Our primary customers are commercial airlines and the U.S. government.",
            ticker="BA",
        )

        draft = ExtractiveAnswerGenerator().generate(
            Question("Who are Boeing's primary customers?"), Evidence((passage,))
        )

        assert (
            draft.segments[0].citations[0].quote
            == "Our primary customers are commercial airlines and the U.S. government."
        )

    def test_each_quote_is_followed_by_its_citation_before_the_line_break(self) -> None:
        draft = ExtractiveAnswerGenerator().generate(Question("What could limit AMD's revenue?"), EVIDENCE)

        assert draft.segments[0].text.endswith("”")
        assert draft.segments[0].citations
        assert draft.segments[1].text == "\n"

    def test_uses_the_analyst_vocabulary_to_find_the_sentence_that_answers(self) -> None:
        passage = make_passage(
            "AMD-10K-2022#0020",
            "We also employ application engineers to assist our customers in designing systems.",
            "One customer accounted for 16% of our consolidated net revenue for the year ended December 31, 2022.",
        )
        generator = ExtractiveAnswerGenerator(vocabulary=AnalystVocabulary.default())

        draft = generator.generate(Question("Did AMD report customer concentration in FY22?"), Evidence((passage,)))

        assert draft.segments[0].citations[0].quote.startswith("One customer accounted for 16%")

    def test_quotes_at_most_three_passages(self) -> None:
        many = Evidence(tuple(make_passage(f"AMD-10K-2022#{n:04d}", f"Fact number {n}.") for n in range(6)))

        draft = ExtractiveAnswerGenerator().generate(Question("What facts are there?"), many)

        assert len([s for s in draft.segments if s.citations]) == 3


@pytest.mark.live
@pytest.mark.skipif(not os.environ.get("ANTHROPIC_API_KEY"), reason="needs ANTHROPIC_API_KEY")
def test_live_answer_cites_the_supporting_passage() -> None:
    client = anthropic.Anthropic(timeout=60.0, max_retries=2)
    generator = ClaudeAnswerGenerator(
        client.beta.messages.create, model="claude-opus-5-5", effort="medium", max_tokens=8000
    )

    answer = GroundingPolicy().assess(generator.generate(QUESTION, EVIDENCE), EVIDENCE)

    assert answer.status in (GroundingStatus.GROUNDED, GroundingStatus.PARTIALLY_GROUNDED)
    assert any(c.passage_id == SUPPLY.id for s in answer.segments for c in s.citations)
