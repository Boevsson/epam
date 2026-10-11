from pathlib import Path

import pytest

from filings_qa.infrastructure.settings import Settings


def test_defaults_point_at_the_repository_data_directory() -> None:
    settings = Settings(_env_file=None)

    assert settings.corpus_file == settings.data_dir / "corpus.yaml"
    assert settings.filings_dir == settings.data_dir / "filings"
    assert settings.index_dir == settings.data_dir / "index"
    assert settings.anthropic_api_key is None


def test_environment_variables_override_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATA_DIR", "/data")
    monkeypatch.setenv("EVIDENCE_SIZE", "5")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    settings = Settings(_env_file=None)

    assert settings.data_dir == Path("/data")
    assert settings.evidence_size == 5
    assert settings.anthropic_api_key is not None
    assert settings.anthropic_api_key.get_secret_value() == "test-key"
    assert "test-key" not in repr(settings)


def test_pipeline_signature_changes_with_anything_that_changes_the_index() -> None:
    base = Settings(_env_file=None)

    assert base.pipeline_signature != Settings(_env_file=None, chunk_max_tokens=300).pipeline_signature
    assert base.pipeline_signature != Settings(_env_file=None, embedding_model="other").pipeline_signature
    assert base.pipeline_signature == Settings(_env_file=None, evidence_size=3).pipeline_signature
