---
paths:
  - "docs/**"
  - "*.md"
---

# Documentation

- `README.md` and `docs/*.md` describe the current state only: no dates of past investigations, run ids, "was/now", or superseded sections — history is in git.
- Dated, point-in-time work lives in `qa/`: reviews, audits, QA reports, research, permission drafts and session briefs. Those files state their date and base commit, may hold numbers measured at that time, and are not rewritten to the current state. Facts that remain true move into `docs/` (known issues into `docs/status.md`), decisions into ADRs, work into Linear.
- Prefer no number to an untested one. Curriculum counts, the tab diagram and cited paths are checked by `tests/test_docs_match_code.py`; do not add doc-count tests for anything else.
- Update or delete a "missing" or "known issue" entry in the same change that resolves it (`docs/status.md`).
- Claims about privacy, cost and provenance are pinned by tests.
- Cite files in backticks with a real path; the doc test checks they exist.
- Keep `AGENTS.md` under 100 lines: only what every session needs.
