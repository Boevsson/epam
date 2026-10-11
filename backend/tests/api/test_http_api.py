from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from filings_qa.entrypoints.http.app import create_app
from filings_qa.research.adapters.snapshot_reader import SnapshotUnavailableError
from filings_qa.research.application.ask_question import AskQuestion
from filings_qa.research.application.list_filings import ListFilings
from filings_qa.research.application.search_passages import SearchPassages
from filings_qa.research.application.services import ResearchServices
from filings_qa.research.domain.grounding import GroundingPolicy
from filings_qa.shared_kernel.values import FilingId
from tests.fakes.research import InMemoryPassageReader, SpyAnswerGenerator, StubRetriever, make_passage

SUPPLY = make_passage("AMD-10K-2022#0001", "We rely on TSMC to manufacture our wafers.", ticker="AMD", page=17)
DEMAND = make_passage("AMD-10K-2022#0002", "PC demand fell in 2022.", ticker="AMD", page=43)
PRICING = make_passage("PFE-10K-2021#0001", "Drug pricing pressure persists.", ticker="PFE", year=2021, page=20)


class DictDocumentLocator:
    def __init__(self, paths: dict[str, Path]) -> None:
        self._paths = paths

    def path_for(self, filing_id: FilingId) -> Path | None:
        return self._paths.get(filing_id)


def services(tmp_path: Path) -> ResearchServices:
    reader = InMemoryPassageReader([SUPPLY, DEMAND, PRICING])
    hybrid = StubRetriever("hybrid", [SUPPLY.id, DEMAND.id, PRICING.id], reader=reader)
    pdf = tmp_path / "AMD_2022_10K.pdf"
    pdf.write_bytes(b"%PDF-1.7 fake")
    return ResearchServices(
        ask=AskQuestion(hybrid, reader, SpyAnswerGenerator(), GroundingPolicy(), evidence_size=2),
        search=SearchPassages({"hybrid": hybrid, "keyword": StubRetriever("bm25", [DEMAND.id], reader=reader)}, reader),
        list_filings=ListFilings(reader),
        documents=DictDocumentLocator({"AMD-10K-2022": pdf}),
        snapshot_version="v-test",
        answer_generator="spy",
    )


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    with TestClient(create_app(lambda: services(tmp_path))) as test_client:
        yield test_client


def test_answers_a_question_with_citations_evidence_and_the_resolved_scope(client: TestClient) -> None:
    response = client.post("/api/v1/questions", json={"question": "Who manufactures AMD's chips?"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "grounded"
    [segment] = body["segments"]
    [citation] = body["citations"]
    assert segment["citation_ids"] == [citation["id"]]
    assert citation["passage_id"] == "AMD-10K-2022#0001"
    assert citation["quote"] == "We rely on TSMC to manufacture our wafers."
    assert citation["pages"] == {"start": 17, "end": 17}
    assert citation["document_url"] == "/api/v1/filings/AMD-10K-2022/document#page=17"
    assert [e["passage_id"] for e in body["evidence"]] == ["AMD-10K-2022#0001", "AMD-10K-2022#0002"]
    assert body["evidence"][0]["retrieval"]["ranks"]["hybrid"]["rank"] == 1
    assert body["scope"] == {"tickers": ["AMD"], "fiscal_years": [], "items": [], "source": "detected"}
    assert body["meta"]["generator"] == "spy"
    assert "retrieval" in body["meta"]["timings_ms"]


def test_explicit_filters_restrict_the_search(client: TestClient) -> None:
    response = client.post(
        "/api/v1/questions", json={"question": "What are the main risks?", "filters": {"tickers": ["pfe"]}}
    )

    body = response.json()
    assert body["scope"]["source"] == "explicit"
    assert [e["passage_id"] for e in body["evidence"]] == ["PFE-10K-2021#0001"]


@pytest.mark.parametrize(
    "payload",
    [{"question": ""}, {"question": "ok?" * 400}, {"question": "Risks?", "filters": {"tickers": ["NOT A TICKER"]}}],
)
def test_invalid_requests_get_problem_details(client: TestClient, payload: dict[str, object]) -> None:
    response = client.post("/api/v1/questions", json=payload)

    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["title"]


def test_search_with_a_chosen_retriever(client: TestClient) -> None:
    response = client.post("/api/v1/search", json={"query": "PC demand", "mode": "keyword", "limit": 5})

    assert response.status_code == 200
    assert [h["passage_id"] for h in response.json()["hits"]] == ["AMD-10K-2022#0002"]


def test_search_rejects_an_unknown_mode(client: TestClient) -> None:
    response = client.post("/api/v1/search", json={"query": "PC demand", "mode": "fuzzy"})

    assert response.status_code == 422
    assert "fuzzy" in response.json()["detail"]


def test_lists_the_indexed_filings(client: TestClient) -> None:
    response = client.get("/api/v1/filings")

    assert sorted(f["filing_id"] for f in response.json()) == ["AMD-10K-2022", "PFE-10K-2021"]


def test_serves_the_original_pdf_inline(client: TestClient) -> None:
    response = client.get("/api/v1/filings/AMD-10K-2022/document")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-disposition"].startswith("inline")


def test_an_unknown_filing_document_is_a_404_problem(client: TestClient) -> None:
    response = client.get("/api/v1/filings/PFE-10K-2021/document")

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/problem+json")


def test_health_and_readiness(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/ready").json() == {"status": "ready", "snapshot": "v-test", "answer_generator": "spy"}


def test_without_an_index_the_service_is_alive_but_not_ready() -> None:
    def no_snapshot() -> ResearchServices:
        raise SnapshotUnavailableError("no index snapshot; run `filings-qa ingest` first")

    with TestClient(create_app(no_snapshot)) as client:
        assert client.get("/health").status_code == 200
        ready = client.get("/ready")
        asked = client.post("/api/v1/questions", json={"question": "What are AMD's risks?"})

    assert ready.status_code == 503
    assert asked.status_code == 503
    assert "filings-qa ingest" in asked.json()["detail"]
