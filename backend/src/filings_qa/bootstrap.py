"""Composition root: the only module that knows concrete adapters and wires them to ports."""

import anthropic

from filings_qa.infrastructure.embeddings import SentenceTransformerEmbedder
from filings_qa.infrastructure.settings import Settings
from filings_qa.infrastructure.snapshot import SnapshotDirectory
from filings_qa.ingestion.adapters.corpus_manifest import YamlCorpusCatalog
from filings_qa.ingestion.adapters.pymupdf_parser import PyMuPdfParser
from filings_qa.ingestion.adapters.snapshot_store import FileSnapshotStore
from filings_qa.ingestion.application.ingest_corpus import IngestCorpus
from filings_qa.ingestion.domain.chunking import Chunker, ChunkingPolicy
from filings_qa.research.adapters.bm25_retriever import Bm25Retriever
from filings_qa.research.adapters.claude_generator import ClaudeAnswerGenerator
from filings_qa.research.adapters.dense_retriever import DenseRetriever
from filings_qa.research.adapters.document_locator import FilingDocumentLocator
from filings_qa.research.adapters.extractive_generator import ExtractiveAnswerGenerator
from filings_qa.research.adapters.snapshot_reader import SqliteSnapshotReader
from filings_qa.research.application.ask_question import AskQuestion
from filings_qa.research.application.fallback_generator import FallbackAnswerGenerator
from filings_qa.research.application.hybrid_retriever import HybridRetriever
from filings_qa.research.application.list_filings import ListFilings
from filings_qa.research.application.ports import Retriever
from filings_qa.research.application.search_passages import SearchPassages
from filings_qa.research.application.services import ResearchServices
from filings_qa.research.domain.fusion import ReciprocalRankFusion, WeightedScoreFusion
from filings_qa.research.domain.grounding import GroundingPolicy

HEADER_TOKEN_ALLOWANCE = 64  # room for the contextual header prepended to every passage


def build_embedder(settings: Settings) -> SentenceTransformerEmbedder:
    return SentenceTransformerEmbedder(settings.embedding_model, query_prompt=settings.embedding_query_prompt)


def build_ingest_corpus(settings: Settings, embedder: SentenceTransformerEmbedder | None = None) -> IngestCorpus:
    embedder = embedder or build_embedder(settings)
    if settings.chunk_max_tokens + HEADER_TOKEN_ALLOWANCE > embedder.max_tokens:
        raise ValueError(
            f"chunk_max_tokens={settings.chunk_max_tokens} leaves no room for the contextual header within "
            f"{embedder.model_name}'s {embedder.max_tokens}-token context: passages would be truncated"
        )
    chunker = Chunker(embedder, ChunkingPolicy(settings.chunk_max_tokens, settings.chunk_overlap_tokens))
    return IngestCorpus(
        YamlCorpusCatalog(settings.corpus_file, filings_dir=settings.filings_dir),
        PyMuPdfParser(),
        chunker,
        FileSnapshotStore(SnapshotDirectory(settings.index_dir), embedder),
        pipeline_signature=settings.pipeline_signature,
    )


def build_research_services(
    settings: Settings, embedder: SentenceTransformerEmbedder | None = None
) -> ResearchServices:
    """Load the live snapshot and wire hybrid retrieval and answer generation. Raises IndexUnavailableError."""
    embedder = embedder or build_embedder(settings)
    reader = SqliteSnapshotReader.open_current(settings.index_dir, expected_embedding_model=settings.embedding_model)
    keyword, semantic = Bm25Retriever(reader), DenseRetriever(reader, embedder)
    hybrid = HybridRetriever(
        [keyword, semantic], ReciprocalRankFusion(k=settings.rrf_k), candidates=settings.retrieval_candidates
    )
    claude = None
    if settings.anthropic_api_key is not None:
        client = anthropic.Anthropic(
            api_key=settings.anthropic_api_key.get_secret_value(), timeout=settings.llm_timeout_seconds, max_retries=2
        )
        claude = ClaudeAnswerGenerator(
            client.beta.messages.create,
            model=settings.llm_model,
            effort=settings.llm_effort,
            max_tokens=settings.llm_max_tokens,
        )
    generator = FallbackAnswerGenerator(claude, ExtractiveAnswerGenerator())
    embedder.embed_query("warm up")  # load the model now, not on the first request
    return ResearchServices(
        ask=AskQuestion(hybrid, reader, generator, GroundingPolicy(), evidence_size=settings.evidence_size),
        search=SearchPassages({"hybrid": hybrid, "keyword": keyword, "semantic": semantic}, reader),
        list_filings=ListFilings(reader),
        documents=FilingDocumentLocator(settings.filings_dir, reader),
        snapshot_version=reader.manifest.version,
        answer_generator="claude" if claude else "extractive",
    )


def build_evaluation(
    settings: Settings, embedder: SentenceTransformerEmbedder | None = None
) -> tuple[SqliteSnapshotReader, dict[str, tuple[Retriever, bool]]]:
    """Retriever configurations to compare: each single retriever, both fusion strategies, and the value of
    scope detection. Returns the reader and {name: (retriever, use_scope_detection)}."""
    embedder = embedder or build_embedder(settings)
    reader = SqliteSnapshotReader.open_current(settings.index_dir, expected_embedding_model=settings.embedding_model)
    keyword, semantic = Bm25Retriever(reader), DenseRetriever(reader, embedder)
    candidates = settings.retrieval_candidates

    def hybrid(fusion: ReciprocalRankFusion | WeightedScoreFusion) -> HybridRetriever:
        return HybridRetriever([keyword, semantic], fusion, candidates=candidates)

    rrf = hybrid(ReciprocalRankFusion(k=settings.rrf_k))
    return reader, {
        "BM25 only": (keyword, True),
        "Dense only": (semantic, True),
        f"Hybrid, RRF (k={settings.rrf_k})": (rrf, True),
        "Hybrid, convex (alpha=0.3)": (hybrid(WeightedScoreFusion(alpha=0.3)), True),
        "Hybrid, convex (alpha=0.5)": (hybrid(WeightedScoreFusion(alpha=0.5)), True),
        "Hybrid, convex (alpha=0.7)": (hybrid(WeightedScoreFusion(alpha=0.7)), True),
        "Hybrid, RRF, without scope detection": (rrf, False),
    }
