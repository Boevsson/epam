# NovaBridge Filings Q&A

Ask natural-language questions about SEC 10-K filings and get concise answers with page-level, verifiable citations.
Retrieval is hybrid (BM25 keyword search plus dense vector search, merged with Reciprocal Rank Fusion), and an LLM
writes the final answer from the retrieved passages.

> **Status: work in progress.** Design and plan: [docs/technical-analysis.md](docs/technical-analysis.md).

## Development

Requirements: Docker, or [uv](https://docs.astral.sh/uv/) for local development.

| Command | What it does |
|---|---|
| `make setup` | Create the local Python 3.12 environment |
| `make check` | Lint, format check, strict type-check, architecture rules and tests |
| `make test ARGS="-k fusion"` | Run a subset of the tests |
| `make docker-check` | The same quality gate inside Docker |

## Data

The corpus is seven 10-K filings from [FinanceBench](https://github.com/patronus-ai/financebench) (Patronus AI),
listed in [data/corpus.yaml](data/corpus.yaml). FinanceBench's open-source questions for these filings
(CC BY-NC 4.0) serve as the evaluation set in
[backend/tests/eval/financebench_subset.jsonl](backend/tests/eval/financebench_subset.jsonl).
