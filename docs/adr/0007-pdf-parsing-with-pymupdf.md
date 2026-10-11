# ADR 0007: PDF parsing with PyMuPDF; 10-K structure as domain logic

**Status:** accepted

## Context
10-K PDFs have running headers, tables of contents, cross-references, combined headings and hundreds of pages of
appended exhibits (PepsiCo: about 420 of 549 pages).

## Decision
- **Parser:** PyMuPDF extracts page text (fast, good reading order) behind a `DocumentParser` port.
- **Domain logic:** cleaning, item detection and chunking are domain logic, with rules learned from the 7 real
  filings and pinned by regression tests:
  - running headers are lines at a page edge on at least 20% of pages;
  - table-of-contents pages are detected by page numbers after headings;
  - items must appear in increasing order, and a heading never continues a sentence;
  - combined headings ("Items 10, 11, 12 and 13") are recognized;
  - the filing ends at "SIGNATURES", which excludes about 1,050 of 1,917 pages of exhibits.

## Consequences
- **License:** PyMuPDF is AGPL-3.0 or commercial. That is acceptable for an internal prototype, but production needs
  a license decision or a swap (pdfplumber, docling) behind the port.
- **Tables:** tables are flattened into text. Numbers stay searchable, but row/column structure is lost.
  Production direction: XBRL facts for figures, and a layout-aware parser.
