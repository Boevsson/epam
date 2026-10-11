import pytest

from filings_qa.research.application.ask_question import AskQuestion, AskQuestionCommand
from filings_qa.research.application.fallback_generator import FallbackAnswerGenerator
from filings_qa.research.application.hybrid_retriever import HybridRetriever
from filings_qa.research.application.list_filings import ListFilings
from filings_qa.research.application.ports import AnswerGenerationUnavailableError
from filings_qa.research.application.search_passages import (
    SearchCommand,
    SearchPassages,
    UnknownSearchModeError,
)
from filings_qa.research.domain.answer import Evidence, GroundingStatus
from filings_qa.research.domain.fusion import ReciprocalRankFusion
from filings_qa.research.domain.grounding import GroundingPolicy
from filings_qa.research.domain.question import InvalidQuestionError, Question
from filings_qa.research.domain.scope import ScopeSource, SearchScope
from filings_qa.shared_kernel.values import ItemCode, Ticker
from tests.fakes.research import InMemoryPassageReader, SpyAnswerGenerator, StubRetriever, make_passage

AMD_SUPPLY = make_passage("AMD-10K-2022#0001", "We rely on TSMC for wafers.", ticker="AMD")
AMD_DEMAND = make_passage("AMD-10K-2022#0002", "PC demand fell in 2022.", ticker="AMD")
PFE_PRICING = make_passage("PFE-10K-2021#0001", "Drug pricing pressure persists.", ticker="PFE", year=2021)
READER = InMemoryPassageReader([AMD_SUPPLY, AMD_DEMAND, PFE_PRICING])


def ask_question(
    retriever: StubRetriever | HybridRetriever, generator: SpyAnswerGenerator | FallbackAnswerGenerator
) -> AskQuestion:
    return AskQuestion(retriever, READER, generator, GroundingPolicy(), evidence_size=2)


class TestHybridRetriever:
    def test_fuses_the_candidates_of_every_retriever_and_is_itself_a_retriever(self) -> None:
        keyword = StubRetriever("bm25", ["AMD-10K-2022#0001", "AMD-10K-2022#0002"])
        dense = StubRetriever("dense", ["AMD-10K-2022#0002", "PFE-10K-2021#0001"])
        hybrid = HybridRetriever([keyword, dense], ReciprocalRankFusion(), candidates=30)

        hits = hybrid.retrieve("supply", SearchScope(), limit=2)

        assert hybrid.name == "hybrid"
        assert [h.passage_id for h in hits] == ["AMD-10K-2022#0002", "AMD-10K-2022#0001"]
        assert set(hits[0].provenance) == {"bm25", "dense"}
        assert keyword.calls == dense.calls == [("supply", SearchScope(), 30)]


class TestAskQuestion:
    def test_answers_from_the_top_ranked_evidence_and_grounds_the_result(self) -> None:
        generator = SpyAnswerGenerator()
        retriever = StubRetriever("hybrid", ["AMD-10K-2022#0001", "AMD-10K-2022#0002", "PFE-10K-2021#0001"])

        result = ask_question(retriever, generator)(AskQuestionCommand("Who manufactures AMD's chips?"))

        [(_, evidence)] = generator.calls
        assert [p.id for p in evidence.passages] == ["AMD-10K-2022#0001", "AMD-10K-2022#0002"]
        assert result.status is GroundingStatus.GROUNDED
        assert [hit.passage.id for hit in result.evidence] == ["AMD-10K-2022#0001", "AMD-10K-2022#0002"]
        assert result.model == "spy-model"

    def test_does_not_call_the_llm_when_nothing_relevant_is_found(self) -> None:
        generator = SpyAnswerGenerator()

        result = ask_question(StubRetriever("hybrid", []), generator)(
            AskQuestionCommand("What is AMD's dividend?")
        )

        assert result.status is GroundingStatus.INSUFFICIENT_EVIDENCE
        assert result.evidence == ()
        assert generator.calls == []

    def test_retrieves_within_the_companies_and_years_named_in_the_question(self) -> None:
        retriever = StubRetriever("hybrid", ["PFE-10K-2021#0001"])

        result = ask_question(retriever, SpyAnswerGenerator())(
            AskQuestionCommand("How is Pfizer's pricing in FY2021?")
        )

        [(_, scope, _)] = retriever.calls
        assert scope.tickers == frozenset({Ticker("PFE")})
        assert result.scope.source is ScopeSource.DETECTED

    def test_explicit_filters_are_used_as_given(self) -> None:
        retriever = StubRetriever("hybrid", ["AMD-10K-2022#0001"])
        explicit = SearchScope(items=frozenset({ItemCode.RISK_FACTORS}))

        ask_question(retriever, SpyAnswerGenerator())(
            AskQuestionCommand("What about Pfizer?", scope=explicit)
        )

        assert retriever.calls[0][1] == explicit

    @pytest.mark.parametrize("text", ["", "  ", "hi", "x" * 1001])
    def test_rejects_empty_or_oversized_questions(self, text: str) -> None:
        with pytest.raises(InvalidQuestionError):
            ask_question(StubRetriever("hybrid"), SpyAnswerGenerator())(AskQuestionCommand(text))

    def test_falls_back_to_quoting_passages_when_the_llm_is_unavailable(self) -> None:
        generator = FallbackAnswerGenerator(
            SpyAnswerGenerator(error=AnswerGenerationUnavailableError("rate limited")),
            SpyAnswerGenerator(name="extractive"),
        )

        result = ask_question(StubRetriever("hybrid", ["AMD-10K-2022#0001"]), generator)(
            AskQuestionCommand("Who manufactures AMD's chips?")
        )

        assert result.status is GroundingStatus.EXTRACTIVE_FALLBACK
        assert result.notice is not None
        assert "rate limited" in result.notice


class TestFallbackAnswerGenerator:
    def test_without_a_primary_generator_the_fallback_answers_with_a_notice(self) -> None:
        fallback = SpyAnswerGenerator(name="extractive")

        draft = FallbackAnswerGenerator(None, fallback).generate(
            Question("What are AMD's risks?"), Evidence((AMD_SUPPLY,))
        )

        assert draft.generator == "extractive"
        assert draft.notice is not None
        assert "no LLM is configured" in draft.notice


class TestSearchPassages:
    def test_searches_with_the_requested_retriever_and_returns_passages_with_ranks(self) -> None:
        search = SearchPassages(
            {"keyword": StubRetriever("bm25", ["AMD-10K-2022#0002"]), "semantic": StubRetriever("dense", [])},
            READER,
        )

        result = search(SearchCommand("PC demand", mode="keyword", limit=5))

        assert [(h.passage.id, h.hit.provenance["bm25"].rank) for h in result.hits] == [
            ("AMD-10K-2022#0002", 1)
        ]

    def test_rejects_an_unknown_mode(self) -> None:
        with pytest.raises(UnknownSearchModeError, match="fuzzy"):
            SearchPassages({"hybrid": StubRetriever("hybrid")}, READER)(SearchCommand("x y z", mode="fuzzy"))


def test_list_filings_returns_every_ingested_filing() -> None:
    filings = ListFilings(READER)()

    assert sorted(f.filing_id for f in filings) == ["AMD-10K-2022", "PFE-10K-2021"]
