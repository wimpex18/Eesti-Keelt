---
paths:
  - "docs/**"
  - "*.md"
---

# Documentation

- Docs describe the current state only. No dates of past investigations, run ids, "was/now", or superseded sections — history is in git.
- Prefer no number to an untested one. Curriculum counts, the tab diagram and cited paths are checked by `tests/test_docs_match_code.py`; do not add doc-count tests for anything else.
- Update or delete a "missing" or "known issue" entry in the same change that resolves it (`docs/status.md`).
- Claims about privacy, cost and provenance are pinned by tests.
- Cite files in backticks with a real path; the doc test checks they exist.
- Keep `AGENTS.md` under 100 lines: only what every session needs.
