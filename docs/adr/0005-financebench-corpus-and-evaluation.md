# ADR 0005: FinanceBench filings as corpus and golden set

**Status:** accepted

## Context
No PDFs came with the brief. Judging "quality of hybrid search" needs ground truth, not anecdotes.

## Decision
- **Corpus:** 7 10-K PDFs from FinanceBench (Patronus AI): AMD, American Express and Boeing FY2022; PepsiCo FY2021
  and FY2022; J&J FY2022; Pfizer FY2021.
- **Selection criteria:** the most open-sample questions, industry diversity, a same-industry pair (J&J/Pfizer), and
  two fiscal years of one company.
- **Golden set:** the 33 matching questions, with evidence pages converted from 0-based to 1-based at the boundary
  (verified on 37 of 40 evidence snippets).
- **Metrics:** Hit@k, MRR@k and Recall@k at page level, via `filings-qa eval`.

## Consequences
- **Fair ablations:** every retrieval change is measured.
- **Small sample:** 33 questions; differences of one or two questions are noise.
- **License:** FinanceBench data is CC BY-NC 4.0, which is fine for a non-commercial prototype; credited in the
  README.
