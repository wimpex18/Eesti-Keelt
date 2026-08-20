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
| **Safari / WebKit** | ✅ | ✅ | whole suite runs on both engines |
| Dark mode | ✅ | — | rendered, screenshotted and read |
| Injected API failures | ✅ | — | drills, check, reading all 500-ed |
| Keyboard & ARIA | ✅ | — | focus order, roving tabindex, arrow keys |

## Defects

Round 1 found five by driving the app; **round 2 found four more by looking at
screenshots of it**, which is the finding about the method rather than the
product. Geometry assertions cannot see a repeated sentence, a database key in
a label, or a stack trace where a message should be.

| id | Severity | Summary | State |
|---|---|---|---|
| **QA-1** | Medium-High | `kõik` showed one band — two thirds of the corpus unreachable | **fixed** — bands interleaved |
| **QA-2** | Medium | No UI state survived a reload; no deep link; Back left the app | **fixed** — hash routing |
| **QA-5** | Medium | Path printed database keys: `astmevaheldus ← gen-stem` | **fixed** — resolved in the API |
| **QA-6** | Medium | A 10-item drill held 5–8 distinct sentences, one repeated ×5 | **fixed** — round-robin over frames |
| **QA-7** | Medium | ARIA tabs pattern half-implemented, arrow keys inert | **fixed** — wiring derived, roving tabindex |
| **QA-8** | Low-Med | Reading failure showed a raw JS TypeError to the learner | **fixed** — reads `detail` |
| **QA-9** | **High** | `ReferenceError: Cannot access 'examLevel' before initialization` on any exam-mode deep link | **fixed** — bootstrap moved to end of script |
| **QA-2b** | Low | Exam level reset to A2 on reload | **fixed** — localStorage |
| **QA-3** | Low | Empty answer consumed a drill item and scored it wrong | **fixed** — nudges instead |
| **QA-4** | Low | Empty writing submission gave no feedback at all | **fixed** — says what is missing |

All ten are fixed. Nothing is left `xfail`.

### QA-9, the one Safari found

Installing WebKit was worth it on the first run. Landing directly on an
exam-mode hash threw `ReferenceError: Cannot access 'examLevel' before
initialization` — the routing bootstrap ran `loadExam()` from a position in the
file above `let examLevel`, a temporal dead zone.

Three things make it the most interesting defect of the whole pass:

1. **It was a regression the QA-2 fix introduced.** Before routing existed the
   first panel was always Rada, so the exam loader never ran that early.
2. **Both engines had it.** Chromium was not immune — the loader is `async`, so
   the failure arrived as an *unhandled rejection*, and nothing was listening
   for those. WebKit reported it as a page error where it could be seen.
3. **Every visibility assertion still passed**, because the panel rendered
   anyway. Only the error channel knew.

The fix is positional rather than a moved declaration: the bootstrap now runs
at the end of the script, so every declaration exists whichever panel the URL
asks for. Moving `examLevel` alone would have fixed this instance and left the
trap armed for the next loader.

### QA-7 in full, because it is the one a person would have felt

The page declared `role="tab"` on 15 buttons inside 5 `role="tablist"`
containers, and implemented none of the rest of the pattern: no
`aria-controls` on any tab, no `role="tabpanel"` on any of the 10 panels, and
**arrow keys that did nothing**. A screen reader announces a tab list, which
tells its user to expect arrow-key navigation and an associated panel; they got
neither. Announcing a pattern you do not honour is worse than plain buttons,
which promise nothing.

Now wired from `data-tab` at load rather than typed into fifteen elements, with
Arrow/Home/End moving and activating, and a roving `tabindex` so Tab steps past
the strip instead of through every button in it.

What *is* right, and was checked: `lang="et"`, exactly one `h1`, every visible
input labelled, every image with `alt`, a visible focus ring on every control,
and a tab order that follows the reading order.

### The two that turned out to be one shape

QA-1 and QA-6 look unrelated — a filter and a drill generator — and are the
same bug twice: **plenty of material, and a selection step that shows a narrow
slice of it.** QA-1 let recency ordering fill the whole limit with one band;
QA-6 let uniform random sampling cluster ten items onto five frames. Both were
invisible to every existing test because each individual row returned was
perfectly valid. When reviewing a selection step, ask what the *set* looks
like, not whether the items are correct.

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
- **Text apparently running under the mobile navigation bar.** The Russian
  caveat at the foot of Edenemine looked clipped in a screenshot. It was not:
  the screenshot was taken at scroll 0. At full scroll the paragraph clears the
  bar. **A screenshot taken before scrolling is not evidence of clipping** —
  scroll first, then look.
- **`kook · A1` offering `koogu` in a drill.** Stale local `data/eesti.db`,
  the same class as the `edge.db` one. Vabamorf returns two paradigms for
  *kook* (the cake, `koogi`; a hooked pole, `koogu`) and current `case_forms`
  correctly refuses ambiguous words. The deployed image rebuilds the dataset,
  so it does not ship — but see the coverage gap below.

## The gap that has no test either way

`test_export_quality` guards `edge.db`, the dataset exported to Cloudflare.
The FastAPI app serves its drills from `eesti.db.object_cases`, and **nothing
guards that table.** A stale copy teaches a wrong paradigm with a straight
face. It does not ship today only because the Dockerfile rebuilds from
scratch; that is a property of the build, not a test.

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
- **Firefox.** Not installed. Chromium and WebKit both run now.
- **Dark mode was checked and passes.** Rendered at `color_scheme=dark`,
  screenshotted and read: the token palette holds, verdict colours stay
  legible, and no element resolves to text-on-its-own-background.
- **Offline / flaky-network behaviour** of the page itself.
- **Keyboard-only navigation and screen readers.** `role="tab"` is present;
  focus order and announcements were not audited.
- **Concurrency** — two tabs open on the same learner state.

## Running the browser suite

```bash
python -m pytest tests/test_e2e_journeys.py -q   # both engines x both viewports
```

132 tests: Chromium and WebKit, desktop and phone. WebKit is included only when
`playwright install webkit` has been run — the suite drops to Chromium alone
rather than failing, but **run it with WebKit before believing a release**: the
worst defect of this whole pass was invisible without it.

It **skips** rather than fails without Playwright, a Chromium binary or a
built dataset, and it is deliberately not wired into CI — the standing
decision is not to put a browser in the build. That means it only protects
anything if somebody runs it; run it before a release, and after any change
to `eesti/web/index.html`.
