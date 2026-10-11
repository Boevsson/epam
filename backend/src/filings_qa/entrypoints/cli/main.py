"""``filings-qa`` command-line interface (driving adapter)."""

import time

import typer

from filings_qa import bootstrap
from filings_qa.infrastructure.settings import Settings

app = typer.Typer(help="Hybrid-search question answering over SEC 10-K filings.", no_args_is_help=True)


@app.callback()
def main() -> None:
    """NovaBridge filings Q&A."""


@app.command()
def ingest(
    force: bool = typer.Option(False, "--force", help="Rebuild even if the corpus is unchanged."),
) -> None:
    """Parse the PDFs listed in corpus.yaml and publish a new index snapshot."""
    settings = Settings()
    started = time.perf_counter()
    report = bootstrap.build_ingest_corpus(settings)(force=force)
    if report.skipped:
        typer.echo("Corpus unchanged since the live snapshot; nothing to do (use --force to rebuild).")
        return
    typer.echo(f"{'filing':<16} {'pages':>5} {'excluded':>10} {'passages':>8}  items")
    for filing in report.filings:
        excluded = str(filing.excluded_pages) if filing.excluded_pages else "-"
        items = " ".join(item.value for item in filing.items)
        typer.echo(
            f"{filing.filing_id:<16} {filing.page_count:>5} {excluded:>10} {filing.passage_count:>8}  {items}"
        )
    total = sum(f.passage_count for f in report.filings)
    elapsed = time.perf_counter() - started
    typer.echo(f"Published snapshot {report.snapshot_version}: {total} passages in {elapsed:.1f}s.")
