"""Configuration from environment variables or a ``.env`` file (12-factor)."""

from pathlib import Path
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

_REPOSITORY = Path(__file__).resolve().parents[4]  # backend/src/filings_qa/infrastructure -> repository
PIPELINE_VERSION = 1  # bump when parsing, cleaning, sectioning or chunking rules change


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(_REPOSITORY / ".env", ".env"), env_file_encoding="utf-8", extra="ignore"
    )

    data_dir: Path = _REPOSITORY / "data"

    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_query_prompt: str = "Represent this sentence for searching relevant passages: "
    chunk_max_tokens: int = 350
    chunk_overlap_tokens: int = 50

    retrieval_candidates: int = 50
    evidence_size: int = 8
    rrf_k: int = 60

    anthropic_api_key: SecretStr | None = None
    llm_model: str = "claude-opus-5-5"
    llm_effort: Literal["low", "medium", "high", "xhigh", "max"] = "medium"
    llm_max_tokens: int = 8000
    llm_timeout_seconds: float = 60.0

    cors_origins: list[str] = ["http://localhost:5173"]

    @property
    def corpus_file(self) -> Path:
        return self.data_dir / "corpus.yaml"

    @property
    def filings_dir(self) -> Path:
        return self.data_dir / "filings"

    @property
    def index_dir(self) -> Path:
        return self.data_dir / "index"

    @property
    def pipeline_signature(self) -> str:
        """Everything that changes the index; part of the corpus fingerprint, so changing it re-ingests."""
        return (
            f"pipeline={PIPELINE_VERSION};embedding={self.embedding_model};"
            f"chunks={self.chunk_max_tokens}/{self.chunk_overlap_tokens}"
        )
