# ADR 0001: Hexagonal architecture with two bounded contexts

**Status:** accepted

## Context
The brief grades architecture and asks for DDD, TDD and SOLID, within a time budget of about ten hours. The system has
two very different flows: batch ingestion (CPU-heavy, offline) and question answering (latency-sensitive).

## Decision
A modular monolith in ports-and-adapters style with two bounded contexts:
- **Filing Ingestion**, a supporting subdomain: PDF to clean lines, then 10-K items, passages and an index snapshot.
- **Research**, the core subdomain: scope resolution, hybrid retrieval, fusion and grounded answers.

Rules:
- The two contexts share only a small kernel (`FilingId`, `Ticker`, `FiscalYear`, `ItemCode`, `PageRange`) and
  exchange data only through the published snapshot format.
- Domain layers are pure Python. Use cases depend on `typing.Protocol` ports. Concrete adapters are wired only in
  `bootstrap.py`.
- import-linter enforces these rules in CI.

## Consequences
- About 80% of the logic is tested in milliseconds without I/O, with fakes for ports and shared contract tests
  proving adapters are interchangeable.
- Swapping BM25, the vector store, the PDF parser or the LLM is a new adapter, not a rewrite.
- No CQRS, event sourcing or microservices: nothing in the brief needs them. The context split is where ingestion
  workers and the query API would separate in production.
