"""The published language between Ingestion (writer) and Research (reader): the on-disk index snapshot.

A snapshot is an immutable directory; ``CURRENT`` names the live one and is switched atomically, so readers
never see a half-written index. Only plain data crosses this boundary (paths, SQL, JSON), never domain types,
which keeps the two bounded contexts independent.
"""

import json
import os
import shutil
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path

FORMAT_VERSION = 2  # 2: filings.source_file
MANIFEST_FILE = "manifest.json"
PASSAGES_FILE = "passages.sqlite"
BM25_DIR = "bm25"
VECTORS_FILE = "vectors.npy"
CURRENT_FILE = "CURRENT"

# row_id is 0..N-1 and doubles as the BM25 document index and the row of the vector matrix.
SCHEMA = """
CREATE TABLE filings (
    filing_id      TEXT PRIMARY KEY,
    company        TEXT NOT NULL,
    ticker         TEXT NOT NULL,
    form           TEXT NOT NULL,
    fiscal_year    INTEGER NOT NULL,
    aliases        TEXT NOT NULL,      -- JSON array
    source         TEXT NOT NULL,      -- sha256 of the source PDF
    source_file    TEXT,               -- its file name, to serve the original for verification
    page_count     INTEGER NOT NULL,
    excluded_start INTEGER,
    excluded_end   INTEGER,
    passage_count  INTEGER NOT NULL
);
CREATE TABLE passages (
    row_id     INTEGER PRIMARY KEY,
    passage_id TEXT NOT NULL UNIQUE,
    filing_id  TEXT NOT NULL REFERENCES filings (filing_id),
    item       TEXT NOT NULL,
    page_start INTEGER NOT NULL,
    page_end   INTEGER NOT NULL,
    header     TEXT NOT NULL,          -- contextual header prepended at indexing time
    text       TEXT NOT NULL,
    sentences  TEXT NOT NULL           -- JSON array: the citable units
);
CREATE INDEX passages_by_filing ON passages (filing_id);
"""


@dataclass(frozen=True, slots=True)
class SnapshotManifest:
    format_version: int
    version: str
    created_at: str
    fingerprint: str
    embedding_model: str
    embedding_dimension: int
    passage_count: int
    filing_ids: tuple[str, ...]

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)

    @classmethod
    def from_json(cls, text: str) -> "SnapshotManifest":
        data = json.loads(text)
        data["filing_ids"] = tuple(data["filing_ids"])
        return cls(**data)


class SnapshotDirectory:
    """Holds versioned snapshot directories under one root, plus the CURRENT pointer."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def current_path(self) -> Path | None:
        pointer = self.root / CURRENT_FILE
        if not pointer.is_file():
            return None
        path = self.root / pointer.read_text().strip()
        return path if path.is_dir() else None

    def read_current_manifest(self) -> SnapshotManifest | None:
        current = self.current_path()
        return SnapshotManifest.from_json((current / MANIFEST_FILE).read_text()) if current else None

    def new_staging(self) -> Path:
        self.root.mkdir(parents=True, exist_ok=True)
        return Path(tempfile.mkdtemp(prefix=".staging-", dir=self.root))

    def publish(self, staging: Path, version: str) -> Path:
        final = self.root / version
        staging.rename(final)
        pointer_tmp = self.root / f".{CURRENT_FILE}.tmp"
        pointer_tmp.write_text(version)
        os.replace(pointer_tmp, self.root / CURRENT_FILE)  # atomic switch
        return final

    @staticmethod
    def discard(staging: Path) -> None:
        shutil.rmtree(staging, ignore_errors=True)
