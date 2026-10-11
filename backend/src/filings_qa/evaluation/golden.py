"""Loads the FinanceBench open-source questions (CC BY-NC 4.0, Patronus AI) as a golden set."""

import json
from collections.abc import Mapping
from pathlib import Path

from filings_qa.evaluation.metrics import GoldenQuestion
from filings_qa.shared_kernel.values import FilingId


def load_financebench(path: Path, filing_ids: Mapping[str, FilingId]) -> list[GoldenQuestion]:
    """`filing_ids` maps FinanceBench doc names (PDF file stems) to our filings; other questions are skipped.

    FinanceBench evidence pages are 0-based; ours are 1-based, so they are converted here, at the boundary.
    """
    questions = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        filing_id = filing_ids.get(row["doc_name"])
        if filing_id is None:
            continue
        pages = frozenset(int(e["evidence_page_num"]) + 1 for e in row["evidence"] if e["doc_name"] == row["doc_name"])
        questions.append(GoldenQuestion(row["financebench_id"], row["question"], filing_id, pages))
    return questions
