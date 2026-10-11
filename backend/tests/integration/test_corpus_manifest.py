import hashlib
from pathlib import Path

import pytest
from filings_qa.ingestion.adapters.corpus_manifest import CorpusManifestError, YamlCorpusCatalog

from filings_qa.shared_kernel.values import FiscalYear, FormType, Ticker

MANIFEST = """
filings:
  - file: PFIZER_2021_10K.pdf
    company: Pfizer Inc.
    ticker: pfe
    form: 10-K
    fiscal_year: 2021
    aliases: ["Pfizer"]
"""


def write(path: Path, content: str | bytes) -> Path:
    path.write_bytes(content.encode() if isinstance(content, str) else content)
    return path


def test_reads_metadata_location_and_hash_of_each_filing(tmp_path: Path) -> None:
    pdf = write(tmp_path / "PFIZER_2021_10K.pdf", b"%PDF-1.7 fake")
    manifest = write(tmp_path / "corpus.yaml", MANIFEST)

    [source] = YamlCorpusCatalog(manifest, filings_dir=tmp_path).sources()

    assert source.metadata.company == "Pfizer Inc."
    assert source.metadata.ticker == Ticker("PFE")
    assert source.metadata.form is FormType.TEN_K
    assert source.metadata.fiscal_year == FiscalYear(2021)
    assert source.metadata.aliases == ("Pfizer",)
    assert source.location == str(pdf)
    assert source.sha256 == hashlib.sha256(b"%PDF-1.7 fake").hexdigest()


def test_a_listed_pdf_that_does_not_exist_is_an_error(tmp_path: Path) -> None:
    manifest = write(tmp_path / "corpus.yaml", MANIFEST)

    with pytest.raises(CorpusManifestError, match="PFIZER_2021_10K.pdf"):
        YamlCorpusCatalog(manifest, filings_dir=tmp_path).sources()


def test_an_invalid_entry_names_the_offending_file(tmp_path: Path) -> None:
    write(tmp_path / "PFIZER_2021_10K.pdf", b"%PDF")
    manifest = write(tmp_path / "corpus.yaml", MANIFEST.replace("fiscal_year: 2021", "fiscal_year: 1900"))

    with pytest.raises(CorpusManifestError, match=r"PFIZER_2021_10K\.pdf.*fiscal year"):
        YamlCorpusCatalog(manifest, filings_dir=tmp_path).sources()
