"""``filings-qa`` command-line interface (driving adapter)."""

import time
from pathlib import Path
from typing import Annotated

import typer

from filings_qa import bootstrap
from filings_qa.infrastructure.settings import Settings

DEFAULT_GOLDEN_SET = Path(__file__).resolve().parents[4] / "tests" / "eval" / "financebench_subset.jsonl"

app = typer.Typer(help="Hybrid-search question answering over SEC 10-K filings.", no_args_is_help=True)


@app.callback()
def main() -> None:
    """NovaBridge filings Q&A."""


@app.command()
def ingest(
    force: Annotated[bool, typer.Option("--force", help="Rebuild even if the corpus is unchanged.")] = False,
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
        typer.echo(f"{filing.filing_id:<16} {filing.page_count:>5} {excluded:>10} {filing.passage_count:>8}  {items}")
    total = sum(f.passage_count for f in report.filings)
    elapsed = time.perf_counter() - started
    typer.echo(f"Published snapshot {report.snapshot_version}: {total} passages in {elapsed:.1f}s.")


@app.command("eval")
def evaluate_retrieval(
    k: Annotated[int, typer.Option(help="Cut-off rank for Hit@k, MRR@k and Recall@k.")] = 10,
    golden: Annotated[Path, typer.Option(help="FinanceBench-format golden questions (JSONL).")] = DEFAULT_GOLDEN_SET,
    output: Annotated[Path | None, typer.Option(help="Also write the Markdown table to this file.")] = None,
) -> None:
    """Compare retrieval configurations on the golden set (page-level ground truth)."""
    from filings_qa.evaluation.golden import load_financebench
    from filings_qa.evaluation.runner import evaluate, markdown_table

    settings = Settings()
    reader, configurations = bootstrap.build_evaluation(settings)
    by_doc = {f.source_name.removesuffix(".pdf"): f.filing_id for f in reader.filings() if f.source_name}
    questions = load_financebench(golden, by_doc)
    table = markdown_table(evaluate(configurations, questions, reader, k=k), k=k)
    typer.echo(f"{len(questions)} questions, snapshot {reader.manifest.version}\n\n{table}")
    if output is not None:
        output.write_text(table + "\n", encoding="utf-8")


@app.command()
def ask(question: Annotated[str, typer.Argument(help="A question about the indexed filings.")]) -> None:
    """Answer a question from the terminal, with numbered citations."""
    from filings_qa.research.application.ask_question import AskQuestionCommand

    result = bootstrap.build_research_services(Settings()).ask(AskQuestionCommand(question))
    numbers: dict[tuple[str, str], int] = {}
    text = ""
    for segment in result.segments:
        marks = "".join(f"[{numbers.setdefault((c.passage_id, c.quote), len(numbers) + 1)}]" for c in segment.citations)
        text += segment.text + marks
    typer.echo(f"\n{text.strip()}\n\nStatus: {result.status.value} · generator: {result.generator}")
    if result.notice:
        typer.echo(result.notice)
    labels: dict[str, str] = {hit.passage.id: hit.passage.label for hit in result.evidence}
    for (passage_id, quote), number in numbers.items():
        typer.echo(f"  [{number}] {labels.get(passage_id, passage_id)}: “{quote[:160]}”")
