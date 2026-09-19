---
paths:
  - "docs/**"
  - "*.md"
---

# Documentation

- Docs describe the current state only. No dates of past investigations, run ids, "was/now", or superseded sections — history is in git.
- A derivable number or structure in a doc is asserted by `tests/test_docs_match_code.py`; add a test when adding such a claim.
- Update or delete a "missing" or "known issue" entry in the same change that resolves it (`docs/status.md`).
- Claims about privacy, cost and provenance are pinned by tests.
- Cite files in backticks with a real path; the doc test checks they exist.
- Keep `AGENTS.md` under 100 lines: only what every session needs.
