# QA / UAT status — web app

First systematic UAT pass: **2026-08-20**, against `main` at `f0e3bc7`
(PR #18 merged), driven in Chromium at 1440×900 and 390×844.

This file is the record the next session resumes from: what was exercised,
what passed, what failed, what is blocked, and what nobody has looked at yet.
It is deliberately separate from `docs/status.md`, which inventories the
*product*; this inventories the *testing*.

## How the app was exercised

A real `uvicorn` process and a real browser, not a test client. Every claim
below was produced by driving the page; nothing is inferred from reading the
source. Where a suspicion could not be confirmed by observation it is listed
under *unconfirmed* rather than as a defect.

## Coverage map

| Area | Desktop | Phone | How |
|---|---|---|---|
| All 3 modes × 10 panels open | ✅ | ✅ | every tab clicked, panel visibility asserted |
| One panel visible at a time | ✅ | ✅ | counted at every tab |
| One navigation bar laid out | ✅ | ✅ | computed style, not the CSS rule |
| Grammar drill: generate → answer → verdict | ✅ | ✅ | wrong answer, empty answer, double submit |
| Reading: list → filter → open → back | ✅ | ✅ | all four band options |
| Word card + `<w>` lookup | ✅ | ✅ | found and not-found words |
| Mark known / add to review | ✅ | — | `/api/vocab/known`, `/api/mine` observed |
| Writing check (offline chain) | ✅ | ✅ | empty, whitespace, nonsense, 5 000 chars |
| Dictation: next → check | ✅ | — | empty submission graded |
| Review queue + FSRS grades | ✅ | — | queue rendered, grade buttons present |
| Exam overview + A2/B1 switch | ✅ | ✅ | content changes, `aria-selected` follows |
| Persistence across reload | ✅ | — | vocabulary status survives; UI state does not |
| Back / forward / deep link | ✅ | ✅ | see QA-2 |
| API validation & errors | ✅ | — | 404 / 422 / 400, no 500s |
| Horizontal overflow | ✅ | ✅ | every tab, both sizes |
| Tap-target floor (32 px) | n/a | ✅ | navigation buttons |

## Defects

| id | Severity | Summary | Regression test |
|---|---|---|---|
| **QA-1** | Medium-High | `kõik` shows only one band — two thirds of the corpus unreachable | `test_library.py::TestBrowsingEverything` (xfail, strict) + E2E |
| **QA-2** | Medium | No UI state survives a reload; no deep link; Back leaves the app | `test_e2e_journeys.py::TestDiscoveredDefects` (xfail, strict) |
| **QA-2b** | Low | Chosen exam level resets to A2 on reload | as above |
| **QA-3** | Low | Empty answer silently consumes a drill item and scores it wrong | none yet — see *unresolved* |
| **QA-4** | Low | Empty writing submission gives no feedback at all | none yet — see *unresolved* |

Full reproduction steps live in the QA report for this session; the tests
carry the reasoning in their `reason=` strings so it survives without the
chat log.

## Not defects — checked and cleared

Recorded because each one *looked* like a defect and cost time to clear, and
the next person should not pay for it twice.

- **The 36-topic path list is collapsed on the phone.** Deliberate, and
  commented as such: a phone hides it behind a disclosure, a laptop has
  1 500 px of empty column. Opened once on load above 1 080 px.
- **Descendants of that collapsed `<details>` still report bounding boxes.**
  Chromium gives them a non-zero rect while `checkVisibility()` is false and
  they are not hit-testable. A layout assertion filtering on rect height alone
  reports six phantom "controls trapped under the navigation". Use
  `checkVisibility()`.
- **The last control on Kuulamine / Rääkimine sits under the navigation before
  scrolling.** After scrolling it is uncovered and hit-tests to itself. Only
  the scrolled state is meaningful.
- **SÕNAVARA did not move after marking a word known.** The word was
  `jätkuma`, frequency rank 20 961; the counter measures the first 4 000. The
  write landed correctly (`vocab_status.status = 5`).
- **The writing check took 6 s on the first call.** The circuit breaker
  learning that TartuNLP's grammar endpoint is dead. Subsequent calls: 0.8 s.
- **Two `test_export_quality` failures on a fresh checkout.** Stale local
  `data/edge.db`; `python -m eesti.cli export` clears them. Already recorded
  in `docs/status.md`.

## Blocked / not testable here

- **Speaking (Rääkimine) end to end.** Needs a microphone and Cloudflare
  Workers AI. The panel, prompts and controls were exercised; recording,
  transcription and pronunciation comparison were not.
- **Anything behind Cloudflare Access.** By design — see CLAUDE.md. The
  deployed app is checked with the `smoke` workflow instead.
- **Notion push.** Requires a real token; the queue was not drained.
- **The paid grammar path.** No provider key locally, so every writing check
  measured the offline chain. The LLM branch of `/api/check` is untested by
  this pass.

## Untested — the honest gaps

- **Töövihikud** beyond its empty state (nothing imported locally).
- **Audio playback** — `▶ Kuula` was never actually heard; TTS was only
  checked for a 200.
- **Real dictation grading accuracy** — one empty submission only.
- **Review scheduling over time.** FSRS intervals cannot be observed in one
  session; grading was exercised, spacing was not.
- **Cross-browser.** Chromium only. No Firefox, no WebKit, no real iOS Safari
  — which matters, because Safari is the likely phone browser here.
- **Offline / flaky-network behaviour** of the page itself.
- **Keyboard-only navigation and screen readers.** `role="tab"` is present;
  focus order and announcements were not audited.
- **Concurrency** — two tabs open on the same learner state.

## Running the browser suite

```bash
python -m pytest tests/test_e2e_journeys.py -q      # ~2.5 min, both viewports
```

It **skips** rather than fails without Playwright, a Chromium binary or a
built dataset, and it is deliberately not wired into CI — the standing
decision is not to put a browser in the build. That means it only protects
anything if somebody runs it; run it before a release, and after any change
to `eesti/web/index.html`.
