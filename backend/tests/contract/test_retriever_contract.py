"""The Retriever contract, run against every implementation (Liskov substitution, made executable)."""

import pytest

from filings_qa.research.adapters.bm25_retriever import Bm25Retriever
from filings_qa.research.adapters.dense_retriever import DenseRetriever
from filings_qa.research.adapters.snapshot_reader import SqliteSnapshotReader
from filings_qa.research.application.hybrid_retriever import HybridRetriever
from filings_qa.research.application.ports import Retriever
from filings_qa.research.domain.fusion import ReciprocalRankFusion
from filings_qa.research.domain.scope import SearchScope
from filings_qa.shared_kernel.values import FiscalYear, ItemCode, Ticker
from tests.fakes.embeddings import HashingEmbedder
from tests.fakes.research import InMemoryKeywordRetriever, InMemoryPassageReader


def in_memory(reader: SqliteSnapshotReader) -> Retriever:
    return InMemoryKeywordRetriever(InMemoryPassageReader(reader.get_many(reader.passage_ids())))


def bm25(reader: SqliteSnapshotReader) -> Retriever:
    return Bm25Retriever(reader)


def dense(reader: SqliteSnapshotReader) -> Retriever:
    return DenseRetriever(reader, HashingEmbedder())


def hybrid(reader: SqliteSnapshotReader) -> Retriever:
    return HybridRetriever([bm25(reader), dense(reader)], ReciprocalRankFusion(), candidates=10)


@pytest.fixture(params=[in_memory, bm25, dense, hybrid], ids=["in-memory", "bm25", "dense", "hybrid"])
def retriever(request: pytest.FixtureRequest, reader: SqliteSnapshotReader) -> Retriever:
    factory = request.param
    return factory(reader)  # type: ignore[no-any-return]


def test_returns_at_most_limit_unique_hits_best_first(retriever: Retriever) -> None:
    hits = retriever.retrieve("revenue supply demand", SearchScope(), limit=3)

    assert 0 < len(hits) <= 3
    assert len({h.passage_id for h in hits}) == len(hits)
    assert [h.score for h in hits] == sorted((h.score for h in hits), reverse=True)


def test_finds_the_passage_that_uses_a_distinctive_term(retriever: Retriever) -> None:
    hits = retriever.retrieve("Who manufactures the wafers? TSMC", SearchScope(), limit=3)

    assert hits[0].passage_id == "AMD-10K-2022#0000"


def test_only_returns_passages_of_the_companies_in_scope(retriever: Retriever, reader: SqliteSnapshotReader) -> None:
    hits = retriever.retrieve("revenue", SearchScope(tickers=frozenset({Ticker("PFE")})), limit=10)

    assert hits
    assert {p.ticker for p in reader.get_many([h.passage_id for h in hits])} == {Ticker("PFE")}


def test_respects_fiscal_year_and_item_restrictions(retriever: Retriever, reader: SqliteSnapshotReader) -> None:
    scope = SearchScope(fiscal_years=frozenset({FiscalYear(2022)}), items=frozenset({ItemCode.RISK_FACTORS}))

    hits = retriever.retrieve("supply chain revenue", scope, limit=10)

    passages = reader.get_many([h.passage_id for h in hits])
    assert passages
    assert all(p.fiscal_year == FiscalYear(2022) and p.item is ItemCode.RISK_FACTORS for p in passages)


def test_a_scope_matching_nothing_returns_no_hits(retriever: Retriever) -> None:
    assert retriever.retrieve("revenue", SearchScope(tickers=frozenset({Ticker("ZZZ")})), limit=5) == []
