"""Composition root: the only module that knows concrete adapters and wires them to ports."""

from filings_qa.infrastructure.embeddings import SentenceTransformerEmbedder
from filings_qa.infrastructure.settings import Settings
from filings_qa.infrastructure.snapshot import SnapshotDirectory
from filings_qa.ingestion.adapters.corpus_manifest import YamlCorpusCatalog
from filings_qa.ingestion.adapters.pymupdf_parser import PyMuPdfParser
from filings_qa.ingestion.adapters.snapshot_store import FileSnapshotStore
from filings_qa.ingestion.application.ingest_corpus import IngestCorpus
from filings_qa.ingestion.domain.chunking import Chunker, ChunkingPolicy

HEADER_TOKEN_ALLOWANCE = 64  # room for the contextual header prepended to every passage


def build_embedder(settings: Settings) -> SentenceTransformerEmbedder:
    return SentenceTransformerEmbedder(settings.embedding_model, query_prompt=settings.embedding_query_prompt)


def build_ingest_corpus(
    settings: Settings, embedder: SentenceTransformerEmbedder | None = None
) -> IngestCorpus:
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
