# ADR 0003: Claude native citations, a grounding policy and an extractive fallback

**Status:** accepted

## Context
Analysts need concise, accurate and verifiable answers. Prompt-based "[1]" markers can point anywhere. The service
must also run without an API key, for reviewers and during outages.

## Decision
- **Native citations:** each passage is sent as a `search_result` block, split into sentences (the citable unit),
  with citations enabled. The API guarantees citations point into supplied results. Quotes are rebuilt from our own
  sentences using the block indices.
- **Grounding policy:** a domain service drops citations outside the evidence or quoting text the passage lacks. It
  computes coverage and sets the status: grounded, partially grounded, insufficient evidence, or extractive fallback.
- **No LLM call without evidence:** if retrieval finds nothing, the LLM is not called.
- **Fallback:** a Decorator switches to the extractive generator (best prose sentence per top passage, quoted)
  when no key is set or the API fails. The answer is clearly labeled.
- **Model settings:** `claude-opus-5-5` with explicit `output_config.effort`; the server-side refusal fallback is
  enabled.

## Consequences
- Citations cannot be combined with structured outputs, so the answer status is derived from citations rather than
  requested as JSON.
- The adapter is a thin humble object: request building and response mapping are pure functions, tested on
  SDK-validated fixtures; one live test runs only with a key.
