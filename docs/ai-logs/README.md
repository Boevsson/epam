# AI assistant conversation logs

The brief asks for the AI assistant conversations used to build this project.

- **Tool:** Claude Code (desktop app), model Claude Opus 5.5.
- **Session 1 (2026-10-11/12):**
  - analysis of the brief and the [technical analysis](../technical-analysis.md);
  - fact-checking of library and dataset details;
  - corpus selection;
  - the full implementation, done test-first and committed in TDD steps;
  - evaluation experiments: fusion strategies, a rejected cross-encoder reranker, analyst-vocabulary query expansion;
  - Docker setup and documentation.
- **Exports:** they live next to this file. A transcript is exported from the app's session menu (Export), which
  produces a zip with the conversation and subagent transcripts.

The commit history shows how the work progressed: `test:` commits precede the `feat:` commits that make them pass.
