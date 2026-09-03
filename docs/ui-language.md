# Which language a string is written in — the audit and its enforcement

The rule itself is in `CLAUDE.md`, because it decides every user-facing string
and a session has to know it before writing one. This is the record of what has
been audited against it and the check that keeps it true.

## What was audited

**Done so far (audit 2026-08-21):** the whole web UI, including the states a
screenshot never reaches — errors, empty states, drill and dictation verdicts,
review grading, progress readouts — plus `aria-label`s, placeholders and the
server-side `detail` messages that surface in the error banner. The readiness
verdict and its reasons, the pronunciation caveat, `library.SECTIONS`
descriptions, the source notes on official material, and the published
integration map. `<html lang>` and the manifest say `ru`, because that is what
the prose is now.

**Still English:** `docs/*.md`, and the API `detail` strings on malformed-
request and operator paths, which a learner cannot provoke. Nothing in `data/`
needs translating — it is the study material.

**The rule is enforced, not remembered.** `tests/test_ui_language.py` had a
hand-written list of forbidden Estonian strings and one of its six entries had
never been in the code — the page said `(või localhost'i)` with parentheses and
the test looked for the version without them, so it passed while the sentence
sat on screen. What replaced it is derived: **labels do not end in a full
stop**, so any sentence-shaped run of user-facing text must contain Cyrillic.
Run against the page before this work it flags 22 strings. The same file checks
that no Estonian grammar term appears in Cyrillic letters, generated from the
term lists rather than listed.

**It scanned half the app.** `pagesrc` collects the page and its modules, which
is where user-facing text was assumed to live — and an explanation *served by
the API* reaches the learner through exactly the same elements. `api/speech.py`
answered `/api/dictation/next` with `Kuula ja kirjuta üles.` and the page wrote
it straight into `#dictState`; the string sat on screen for months while the
check that forbids it by name passed every run. The forbidden list is one
constant now, and two tests read it: one over the page and its modules, one
over `eesti/api/`. Found on 2026-09-03 by reading the phone, not the file.


## Where the misspelling came from

`omastav` reached the screen as **омастав** in nine explanation strings, and
the check written to prevent that then failed to see it typed straight back
into `mining.py` — because the check's list of modules to scan was itself
hand-maintained. It is derived now: any module containing Cyrillic is prose and
is scanned, minus the repair table and the comments that have to quote the
misspelling in order to explain it. The full entry is in `docs/lessons.md`,
under *Derived, never hand-maintained*.
