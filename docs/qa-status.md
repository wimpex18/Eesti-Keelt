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

## The 2026-09-03 pass — the redesign

Second systematic pass, against the redesigned page. Same method: a real
`uvicorn`, a real browser, both viewports, every claim produced by driving the
page. The corpus was built for it (`build`, `export`, `harvest-reading`,
`harvest`, `harvest-exam` — 542 items), which matters: the first pass could not
open a library item, a workbook or an exam task because none were indexed, and
those surfaces had never been looked at.

**What it found, in the order the defects were noticed.** Every one of these
was invisible to 1 600 passing tests.

| Defect | Where |
|---|---|
| Primary button white on the dark theme's mint accent — 2.23:1 | every screen |
| Dictation wrote "why there is no dictation" into an element inside the box it then hid | Kuulamine |
| That note, and the exercise instruction, were Estonian | `api/speech.py` |
| Word card said "не найдено" when the API had said `run cli export first` | Sõnavara, Lugemine |
| `lookup._db` memoised the ABSENCE of the forms database | every lookup |
| The e2e fixture gated the reading journeys on the content file EXISTING | the suite itself |
| Deep-linking `#write` left the selected chip 512px outside the row | phone |
| The skills row bled 24px where `.wrap` pads 20 — 4px of sideways scroll | below 720px |
| Focus ring clipped by the row's own `overflow-x` | keyboard, phone |
| `harjuta` 32px, disclosures 23px, workbook and exam links 15–23px | inside every panel |
| One amber banner for an error, a reference and a mastery message | Rada, Kirjutamine |
| Three rating buttons wrapping ragged, 112px tall | Järjekord |
| `--bg` moved and the status bar, splash and offline page kept the old white | outside the page |

**What was exercised as a learner**, not asserted from the DOM: a path drill
answered wrong then right; a free-practice session with filters; the reading
list, reader, word card, translate refusal and back; the vocabulary list, its
three filters, pagination and all three card actions; dictation played, scored
word by word and advanced; a review card revealed, graded and locked; a
fifteen-item checkpoint answered to a verdict; the archive opened with audio
and transcript; workbooks and exam material listed; the theme cycled through
its three states; deep links, reload and Back.

**Conditions checked beyond the two viewports:** 320px, landscape 844×390, a
20px root font, a narrow desktop window, and both themes.

**Still not covered:** WebKit — no build is installed here, so Safari, the
engine this learner's phone actually uses, remains untested. Recording and
microphone permission cannot be driven headlessly. The Notion queue needs a
correction with a proposed fix, which the offline chain does not produce.

## Running the browser suite

```bash
python -m eesti.cli fetch-data && python -m eesti.cli build
python -m eesti.cli export            # the forms every word card reads
python -m eesti.cli harvest-reading   # the reading journeys need texts
python -m pytest tests/test_e2e_journeys.py -q   # both engines x both viewports
```

All three data steps are gated. Before 2026-09-13 `export` was not, and a
checkout without it ran the journeys and failed 24 of them with
"такого слова в словаре нет" instead of skipping and naming the step.

**First run on a Mac, 2026-09-13** (Python 3.13, Playwright Chromium and
WebKit, 349 texts): **168 passed, 2 skipped** — the two skips are the
tap-target floor, which applies to touch viewports only. Getting there found
three defects in the suite itself, none in the app:

| Defect | Why nobody saw it |
|---|---|
| Browsers looked for only in `/opt/pw-browsers`, and Chromium only as `chrome-linux/chrome` — every journey skipped on macOS with "run `playwright install chromium`" right after it had run | the cloud container is Linux with that path |
| The word card was read the moment it unhid, while it still held the loading skeleton | Chromium lost that race most runs; the cloud had timing that let it pass |
| The flashcard word was keyed by viewport, not engine, on a server both engines share — WebKit found the card Chromium had graded and timed out | only visible with WebKit installed, which the cloud container did not have |

Run the file on its own. In one `pytest tests/` invocation after the
in-process suite, 22 journeys errored in setup on `page.goto` timing out —
the same journeys pass alone. Cause not measured yet.

85 tests per engine: Chromium and WebKit, desktop and phone. WebKit is included only when
`playwright install webkit` has been run — the suite drops to Chromium alone
rather than failing, but **run it with WebKit before believing a release**: the
worst defect of this whole pass was invisible without it.

It **skips** rather than fails without Playwright, a Chromium binary or a
built dataset, and it is deliberately not wired into CI — the standing
decision is not to put a browser in the build. That means it only protects
anything if somebody runs it; run it before a release, and after any change
to `eesti/web/` — the page, the stylesheet or any module under `web/js/`.

## A skip that CI could not see — 2026-09-11

`tests/test_evkk_mapping.py` guards the tag map that weights the whole
curriculum: if a `TAG_MAP` name stops matching EVKK's taxonomy, that tag
silently weighs **zero** and the topic order shifts with nothing to say why.

All three of its checks needed a cached copy of EVKK's page, which is
git-ignored — so **all three skipped in CI**, and the run still read green.
That is the same defect this project has paid for five times in other costumes:
something that looks measured and is not.

### The decision, and the two options that were refused

**Commit a fixture — no.** `sources.REGISTRY` records EVKK as "no explicit
reuse licence on the corpus", `redistributable = 0`. The taxonomy page is TLU's
work, and committing it to a public repository is redistribution — the thing
this project refuses for ERR, HARNO and Selges keeles. A test fixture is not an
exception to that rule; it is the same bytes in a different directory.

**Let CI fetch it — no, twice over.** The host answered 500 on two of three
attempts the day this was written and takes 21 s when it works, so the test
would be flaky, and this project's rule is that a failing test is never written
off as infra. It would also hit a research server on every push, which is the
discourtesy it already refuses toward Sõnaveeb.

### What was done instead: split by what each check actually needs

| Check | Needs | Runs in CI |
|---|---|---|
| the unmapped remainder is counted, not dropped | arithmetic over *any* taxonomy | **yes** |
| no mapped subtree swallows a differently-tagged node | `TAG_MAP` + `LEAF_ONLY` + a tree *shape* | **yes** |
| every tag it weights is one the error log uses | `TAG_MAP` + `config.TAGS` | **yes** |
| a name matching nothing weighs zero | the failure mode, reproduced offline | **yes** |
| every mapped name is really on the page | the live page, irreducibly | no — see below |

The first four are invariants of **our own code**, and they are proved against a
taxonomy this project writes itself: real `TAG_MAP` names, invented structure
and counts. Nothing of TLU's is in the repository. **Five checks now run in CI
where none did.**

### And the live check moved to where live data exists

The last one cannot be faked, so it stopped pretending to live in CI.
`cli evkk` already fetches the real taxonomy, and now **refuses to exit 0 if any
tag weighs zero**, naming the tags and where to fix them. That is strictly
better than a CI test against a snapshot: it runs on real data every time the
taxonomy is actually read, rather than on whatever copy someone happened to
leave on a laptop.

It does not raise. A rename does not make the taxonomy unusable and the counts
are still worth storing — but a weighting that has quietly gone wrong must not
pass for a good run.

### The parser was the real gap, and it needed no fixture from them

Raised on review: the licence objection was being applied too widely. This
project's own note draws the line already — *"Counts about a published taxonomy
are facts; the texts are not"* (`source-gaps.md`) — and the taxonomy counts are
already stored in `content.db` and pushed to the deployment. The posture that
protects ERR's transcripts and HARNO's exam papers was never meant to reach a
list of category names.

Following that through found a better gap than the one being argued about.
`evkk.parse()` **was not tested at all.** Every check built `Mark` objects
directly, so `_ROW_RE`, the markup flattening and the id-placeholder filter had
no coverage — and a restyle of their page is the single most likely thing to
break this harvester.

That needs a fixture **in their format**, not a copy of their file, and a format
can be reproduced without reproducing anyone's data: the shape is faithful — a
`margin-left` div, an anchor whose href carries ancestry as `global_N/`
segments, a `<span>` with the count, real newlines between them — and every
name, id and number in it was made up here. The same approach as the EKI TSV
and PSV XML fixtures.

Seven more checks, all running in CI: labelled nodes found, the count read off
the span, ancestry taken from the URL rather than the indentation, markup
inside a label joined with a space rather than run together, a node labelled
with its own id dropped, a page that stopped matching returning nothing rather
than guessing, and subtree totals reaching ancestors.

**Twelve checks run in CI where none did this morning.**

### The skip is no longer silent

`evkk: absent (tag-map check vs the live page skips -- `cli evkk`)` is now in
the one-line banner the suite prints before and after every run, beside the
word list, the corpus and the browsers. A skip nobody can see is the defect;
a skip that announces itself is a state.
