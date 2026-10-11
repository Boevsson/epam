from pathlib import Path

import pytest

from filings_qa.research.adapters.snapshot_reader import (
    SnapshotIncompatibleError,
    SnapshotUnavailableError,
    SqliteSnapshotReader,
)
from filings_qa.shared_kernel.values import FiscalYear, ItemCode, PageRange, PassageId, Ticker


def test_reads_passages_in_the_requested_order_and_skips_unknown_ids(reader: SqliteSnapshotReader) -> None:
    passages = reader.get_many(
        [PassageId("PFE-10K-2021#0001"), PassageId("nope"), PassageId("AMD-10K-2022#0000")]
    )

    assert [p.id for p in passages] == ["PFE-10K-2021#0001", "AMD-10K-2022#0000"]
    first = passages[1]
    assert (first.company, first.ticker, first.fiscal_year) == (
        "Advanced Micro Devices, Inc.",
        Ticker("AMD"),
        FiscalYear(2022),
    )
    assert (first.item, first.pages, first.sentences) == (
        ItemCode.RISK_FACTORS,
        PageRange.single(17),
        ("We rely on TSMC to manufacture our wafers.",),
    )


def test_summarizes_the_indexed_filings(reader: SqliteSnapshotReader) -> None:
    summaries = {f.filing_id: f for f in reader.filings()}

    assert sorted(summaries) == ["AMD-10K-2022", "PEP-10K-2022", "PFE-10K-2021"]
    assert summaries["PFE-10K-2021"].passage_count == 2
    assert summaries["PFE-10K-2021"].aliases == ("Pfizer",)


def test_refuses_a_snapshot_built_with_another_embedding_model(snapshot_dir: Path) -> None:
    with pytest.raises(SnapshotIncompatibleError, match="re-run ingestion"):
        SqliteSnapshotReader.open(snapshot_dir, expected_embedding_model="another-model")


def test_reports_a_missing_snapshot_clearly(tmp_path: Path) -> None:
    with pytest.raises(SnapshotUnavailableError, match="filings-qa ingest"):
        SqliteSnapshotReader.open_current(tmp_path, expected_embedding_model="any")
