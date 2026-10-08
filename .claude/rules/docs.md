---
paths:
  - "docs/**"
  - "*.md"
---

# Documentation

- Every Markdown file describes the current state: no "was/now", run ids or superseded sections — history is in git. Delete a file when it no longer applies.
- `qa/` holds the review and roadmap (`qa/architecture-review.md`), the source permission drafts and the next-session prompt. Keep them current in the same change that makes them untrue; a measured number there names the commit or date it was measured on. Current facts and known issues belong in `docs/` (`docs/status.md`), decisions in ADRs, follow-up in a comment on its existing Linear issue (no new issues; `AGENTS.md`).
- Prefer no number to an untested one. Curriculum counts, the tab diagram and cited paths are checked by `tests/test_docs_match_code.py`; do not add doc-count tests for anything else.
- Update or delete a "missing" or "known issue" entry in the same change that resolves it (`docs/status.md`).
- Claims about privacy, cost and provenance are pinned by tests.
- Cite files in backticks with a real path; the doc test checks they exist.
- Keep `AGENTS.md` under 100 lines: only what every session needs.
