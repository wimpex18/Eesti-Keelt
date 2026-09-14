---
paths:
  - "tests/**"
---

# Tests

- Build fixtures with the app's own openers and writers; never hand-roll a schema.
- Redirect every database, and pass paths explicitly in class- or session-scoped fixtures (they run before the autouse redirect).
- Safety properties (read-only, no file created) are checked in a **subprocess** with the real argument form, comparing artefacts byte for byte.
- Test behaviour, not source text. When scanning code, parse with `ast` or strip comments: a comment mentioning a name is not a use.
- A guard against a hand-maintained list must not itself be a hand-maintained list.
- Anything scheduled in time is tested by advancing time.
- A reproduction must reproduce the ordering and sizes that trigger the bug.
- A comment recording a fixed bug is not a test: add the test.
- Parsers of third-party markup are tested with synthetic markup (real ERR/Selges text is owner-only).
- Suspect the harness when a suite exercising the culprit stays green (in-process vs subprocess, fixtures vs real paths).
- Verify "works in CI" in a clean `git worktree` — `data/` is git-ignored.
- Browser tests listen for `pageerror` **and** unhandled rejections; run both Chromium and WebKit.
