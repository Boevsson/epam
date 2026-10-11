# ADR 0006: Query expansion with an analyst vocabulary

**Status:** accepted

## Context
Analysts ask about "capex", "quick ratio" or "PP&E"; filings say "purchases of property, plant and equipment",
"current assets" and "property, plant and equipment, net". Neither BM25 nor a general-purpose embedding model bridges
this gap. A general cross-encoder reranker over the hybrid top 50 did not help:
- before expansion, MiniLM-L6 left Hit@10 at 0.58 and bge-reranker-base dropped it to 0.52;
- after expansion, MiniLM-L6 lowered Hit@10 from 0.67 to 0.58;
- it adds 0.5 to 3 s of latency.

It was not adopted.

## Decision
A domain service, `AnalystVocabulary`, appends the filing wording of recognized analyst terms to retrieval queries
(13 generic metric groups). It is applied through a `QueryExpandingRetriever` decorator around each retriever. The
LLM still sees the original question.

## Consequences
- Hybrid Hit@10 rose from 0.58 to 0.67, MRR@10 from 0.20 to 0.32, Recall@10 from 0.53 to 0.64.
- **Caveat:** the glossary is generic analyst vocabulary, but it was written after reading the evaluation questions,
  so the gain is in-sample until confirmed on held-out questions.
- **Production direction:** grow the glossary from real question logs, or rewrite queries with an LLM.
