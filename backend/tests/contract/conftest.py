"""A small snapshot built through the real ingestion side, read back by the research adapters."""

from pathlib import Path

import pytest

from filings_qa.infrastructure.snapshot import SnapshotDirectory
from filings_qa.ingestion.adapters.snapshot_store import FileSnapshotStore
from filings_qa.ingestion.domain.chunking import Chunk
from filings_qa.ingestion.domain.filing import Filing, FilingMetadata
from filings_qa.research.adapters.snapshot_reader import SqliteSnapshotReader
from filings_qa.shared_kernel.values import FiscalYear, FormType, ItemCode, PageRange, Ticker
from tests.fakes.embeddings import HashingEmbedder

CORPUS = {
    ("AMD", "Advanced Micro Devices, Inc.", 2022): [
        (ItemCode.RISK_FACTORS, 17, "We rely on TSMC to manufacture our wafers."),
        (ItemCode.RISK_FACTORS, 18, "Supply constraints could limit our revenue growth."),
        (ItemCode.MD_AND_A, 43, "Revenue increased due to data center demand."),
    ],
    ("PFE", "Pfizer Inc.", 2021): [
        (ItemCode.RISK_FACTORS, 20, "Drug pricing reform could reduce our revenue."),
        (ItemCode.BUSINESS, 9, "Comirnaty vaccine sales grew strongly."),
    ],
    ("PEP", "PepsiCo, Inc.", 2022): [
        (ItemCode.MD_AND_A, 40, "Snack demand rose in North America."),
        (ItemCode.RISK_FACTORS, 14, "Commodity costs and supply chain disruptions could hurt margins."),
    ],
}


def corpus_filings() -> list[Filing]:
    filings = []
    for (ticker, company, year), passages in CORPUS.items():
        metadata = FilingMetadata(company, Ticker(ticker), FormType.TEN_K, FiscalYear(year), (company.split()[0],))
        chunks = [Chunk(item, PageRange.single(page), (text,)) for item, page, text in passages]
        filings.append(Filing.from_chunks(metadata, source_sha256="c" * 64, page_count=200, chunks=chunks))
    return filings


@pytest.fixture(scope="session")
def snapshot_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    directory = SnapshotDirectory(tmp_path_factory.mktemp("index"))
    FileSnapshotStore(directory, HashingEmbedder()).publish(corpus_filings(), fingerprint="contract")
    current = directory.current_path()
    assert current is not None
    return current


@pytest.fixture(scope="session")
def reader(snapshot_dir: Path) -> SqliteSnapshotReader:
    return SqliteSnapshotReader.open(snapshot_dir, expected_embedding_model=HashingEmbedder.model_name)
