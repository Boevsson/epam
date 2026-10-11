"""Finds the original PDF of a filing so the UI can open it at the cited page."""

from pathlib import Path

from filings_qa.research.application.ports import PassageReader
from filings_qa.shared_kernel.values import FilingId


class FilingDocumentLocator:
    def __init__(self, filings_dir: Path, passages: PassageReader) -> None:
        self._root = filings_dir.resolve()
        self._names = {f.filing_id: f.source_name for f in passages.filings() if f.source_name}

    def path_for(self, filing_id: FilingId) -> Path | None:
        name = self._names.get(filing_id)
        if name is None:
            return None
        path = (self._root / name).resolve()
        # The name comes from our own snapshot, but never serve anything outside the filings directory.
        return path if path.parent == self._root and path.is_file() else None
