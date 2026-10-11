import json
from pathlib import Path

from filings_qa.evaluation.golden import load_financebench
from filings_qa.shared_kernel.values import FilingId


def test_converts_zero_based_evidence_pages_and_maps_documents_to_filings(tmp_path: Path) -> None:
    rows = [
        {
            "financebench_id": "fb_1",
            "doc_name": "AMD_2022_10K",
            "question": "Q1?",
            "evidence": [
                {"doc_name": "AMD_2022_10K", "evidence_page_num": 11, "evidence_text": "..."},
                {"doc_name": "AMD_2022_10K", "evidence_page_num": 42, "evidence_text": "..."},
            ],
        },
        {"financebench_id": "fb_2", "doc_name": "NETFLIX_2017_10K", "question": "Q2?", "evidence": []},
    ]
    path = tmp_path / "subset.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in rows))

    questions = load_financebench(path, {"AMD_2022_10K": FilingId("AMD-10K-2022")})

    assert len(questions) == 1
    assert questions[0].id == "fb_1"
    assert questions[0].filing_id == "AMD-10K-2022"
    assert questions[0].pages == frozenset({12, 43})
