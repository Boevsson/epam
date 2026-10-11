# ADR 0002: Hybrid retrieval with our own Reciprocal Rank Fusion

**Status:** accepted

## Context
10-K questions mix exact terms (line items, tickers, "Item 7A") with paraphrase ("geopolitical tension" vs "trade
restrictions"). BM25 scores are unbounded and query-dependent, while cosine similarities sit in a narrow band, so
raw scores cannot simply be added. The brief grades "the quality of the hybrid search implementation".

## Decision
- **Retrievers:** BM25 (bm25s, finance-aware tokenizer) and dense retrieval (bge-small-en-v1.5).
- **Fusion:** Reciprocal Rank Fusion, k=60, implemented in the domain as a pure, property-tested function.
- **Alternative kept:** a convex combination of min-max normalized scores, as a second strategy for the evaluation.
- **Composite:** `HybridRetriever` is itself a `Retriever`.
- **Explainability:** every hit keeps per-retriever provenance (rank and raw score), shown in the API and UI.

## Consequences
- **Measured on 33 FinanceBench questions:** hybrid RRF reaches Hit@10 0.67 vs 0.58 (BM25) and 0.55 (dense), and RRF
  beat the convex combination at α ∈ {0.3, 0.5, 0.7} (see `docs/evaluation-results.md`).
- RRF discards score magnitude, so it cannot say "nothing is relevant". That is handled by the grounding policy and
  the LLM's instruction to decline.
- Not using LangChain's `EnsembleRetriever` means more code to own, but the graded logic is transparent and tested.
