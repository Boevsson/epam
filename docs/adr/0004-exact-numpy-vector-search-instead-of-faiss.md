# ADR 0004: Exact NumPy vector search instead of FAISS

**Status:** accepted (supersedes the original plan of FAISS `IndexFlatIP`)

## Context
- The corpus has about 2.4k passages × 384 dimensions.
- faiss-cpu and torch wheels each bundle their own OpenMP runtime. On macOS, loading both aborts the process
  ("OMP: Error #15"). The documented workaround, `KMP_DUPLICATE_LIB_OK`, is unsafe.

## Decision
The dense retriever computes exact cosine similarity with one NumPy matrix-vector product over a memory-loaded matrix,
with the scope applied as a row mask.

## Consequences
- Same results as an exact FAISS index, well under a millisecond, one dependency fewer, and no crash on any OS.
- **Scaling path:** an approximate index (FAISS HNSW, Qdrant or OpenSearch) behind the same `Retriever` port once the
  corpus reaches hundreds of thousands of passages.
