"""Corpus catalog backed by ``data/corpus.yaml`` and the PDFs next to it."""

import hashlib
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import yaml

from filings_qa.ingestion.application.ports import FilingSource
from filings_qa.ingestion.domain.filing import FilingMetadata
from filings_qa.shared_kernel.errors import DomainError
from filings_qa.shared_kernel.values import FiscalYear, FormType, Ticker


class CorpusManifestError(Exception):
    """The corpus manifest is malformed or points to a missing PDF."""


class YamlCorpusCatalog:
    def __init__(self, manifest: Path, *, filings_dir: Path) -> None:
        self._manifest = manifest
        self._filings_dir = filings_dir

    def sources(self) -> Sequence[FilingSource]:
        document = yaml.safe_load(self._manifest.read_text(encoding="utf-8")) or {}
        return [self._source(entry) for entry in document.get("filings", [])]

    def _source(self, entry: dict[str, Any]) -> FilingSource:
        file_name = entry.get("file", "<missing file>")
        try:
            metadata = FilingMetadata(
                company=str(entry["company"]),
                ticker=Ticker.parse(str(entry["ticker"])),
                form=FormType(str(entry["form"])),
                fiscal_year=FiscalYear(int(entry["fiscal_year"])),
                aliases=tuple(str(alias) for alias in entry.get("aliases", [])),
            )
        except (KeyError, TypeError, ValueError, DomainError) as error:
            raise CorpusManifestError(f"{file_name}: {error}") from error
        path = self._filings_dir / file_name
        if not path.is_file():
            raise CorpusManifestError(f"{file_name}: no such file in {self._filings_dir}")
        return FilingSource(metadata=metadata, location=str(path), sha256=_sha256(path))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()
