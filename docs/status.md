# Where version 1.0 stands

Written 2026-08-20 at the close of the first build, and revised the same day
after the deployment was actually asked how it was doing. This is the honest
inventory: what works, what was never built, what is knowingly broken, and what
the original research plan promised and did not deliver.

Read `roadmap.md` for *why* things were chosen and `lessons.md` for the habits
that came out of getting them wrong.

## The decision this version closes on

**No exam in 2026.** The optional A2 rehearsal (register by 01.10.2026, sit
07.11.2026) was considered and declined on 2026-08-20. The plan is independent
study plus a tutor through the winter, and a sitting in 2027 — either A2 and
then B1, or B1 alone, whenever the evidence supports it.

The app reflects that: `readiness.TARGET` is `None`, the countdown reads
*"экзамен ещё не выбран"*, and `EXAMPLE_TARGET` keeps the calendar shape so
setting a 2027 date is one line. Both levels stay first-class, because *which*
of those two routes to take is precisely what the readiness verdict is for.

## What works

| | |
|---|---|
| **Drills** | 26 of 36 curriculum topics generate items — **24 on a checkout with no harvested corpus**, measured 2026-08-21 by asking `/api/practice` for every topic in `/api/curriculum` rather than by counting generators. Object case, verb forms, conjugation, locative cases, comparison, numerals, question words, word order, punctuation, rection. |
| **Grading** | Deterministic everywhere. No model decides whether an answer is right. |
| **Reading** | 349 Selges keeles texts, click-to-look-up, known-word tracking, comprehensibility ordering. |
| **Listening** | Dictation from the corpus, TTS on any text at 0.7×, ERR episode audio. |
| **Writing** | Grammar check through the provider chain, corrections queued for the Notion error log with an explicit send step. |
| **Speaking** | Question bank in the exam's paired shape, TTS voicing the other side, links out to EKI's own pronunciation exercises. |
| **Review** | FSRS-6 over items you actually got wrong, plus words mined from reading. Intervals expand as they should — measured 2026-08-21 at the due date: 10 min → 2 d → 11 d → 47 d → 171 d → 514 d. |
| **Vocabulary** | `Sõnavara` lists the wordlist by CEFR level, part of speech and what you have marked, commonest first. Same word card as the reader, so a word chosen here and a word met while reading are one thing. |
| **Meaning** | **294 Russian glosses ship with the app** (`data/seed_glossary.tsv`), covering 81 % of the words drills actually use — measured 0 % before. Written for this project, never scraped. Sõnaveeb enriches on demand with senses, rection and muuttüüp; the seed is a baseline, not a ceiling. Sentence-level translation from TartuNLP, on request only. |
| **Rules** | **22 of 23 drillable topics link to the handbook** (was 5). Every section number read off the EKK rather than inferred — a summarising fetch of the same page returned numbers shifted by one. `kusisonad` has none: no section covering question words was found, and a wrong link is worse than none. |
| **Back-translation** | The writing check reads your Estonian back in Russian, so a sentence that is well formed but says the wrong thing is visible. |
| **Verdict** | Four exam parts reported separately, never as one total, with the reasons named in Russian. |
| **Offline** | Installable, and an installed copy now opens without a connection and says why it can do no more. The API is never cached — every endpoint is either the learner's own state or freshly generated, and a drill quietly a day old is worse than one unavailable. |
| **Deployment** | Cloudflare Worker + Access in front of Cloud Run, both free tiers, state snapshotted across cold starts. |

51 API routes, every one with a caller — `test_route_inventory.py` fails on one nothing can reach. 1 432 in-process tests, plus 72 browser journeys run once per engine (Chromium and WebKit, so 144 when both are installed).

## What a learner still cannot do

Measured 2026-08-22 against the code, not inferred from the last time this
section was written.

**This section listed three things on 2026-08-21 and all three were built
within the day** — the vocabulary browser, the empty-topic message, and the
service worker. It stayed as written for a further sprint, which means the one
section a fresh session reads to decide what to build was describing an app
three days out of date. Rebuilding `Sõnavara` from it would have been a
reasonable thing to do and a complete waste. Check this section against the
code before trusting it; better, delete an entry the moment it ships.

### The reading library is not joined to the practice

`library.related()` selects the texts that demonstrate a grammar topic, and
`/api/practice` returns them alongside the drill — "the join that makes
practice and the reading library one tool", as the comment there says. It
reads `topic_items`, and that table is **empty**: `cli link-topics` fills it
and has not been run since the corpus was last rebuilt. The reader returns
`[]`, the practice response carries an empty `reading` list, and nothing
anywhere says so.

Unknown on the deployment. The smoke check verifies `/api/library` *answers*;
it does not count rows in the join, which is the same "presence of a database
is not presence of data" mistake in a new place.

### Only one grammar provider is actually configured

The chain is built for redundancy across five providers and has none: the deep
smoke check on 2026-08-22 read `llm:openrouter: HTTPError 429` with `groq`,
`workers-ai` and `anthropic` all `unavailable` — no key. So the writing check
falls to `vabamorf-offline` whenever the one free tier is spent, which for a
50/day allowance is a normal Tuesday rather than an incident.

Nothing to fix in code: a second key is an operator action, and adding one
would make the chain do what it was designed to do.

## What was never built

### 10 curriculum topics have no generator

```
tahestik  lauseehitus  asesonad  astmevaheldus  kaassonad  sidesonad
maarsonad  tulevik  uhendverbid  liitsonad
```

It was 13 that morning: `pohivormid`, `eitus` and `uhildumine` were built on 2026-08-21. **Do not
maintain this list by hand** — it is `[t.id for t in TOPICS if not t.generator]`,
and the version above is a snapshot for reading, not the source. A test that
kept its own copy of the same set went stale the moment those two landed.

They appear in the syllabus and in the path, and practising them opens a
message saying so rather than nothing. Some are deliberate — `astmevaheldus` is
reference material whose contrast is already drilled through `gen-stem`, where
the stem is actually chosen. Most are simply not done. `uhildumine`,
`uhendverbid` and `liitsonad` were investigated as candidates for the
attested-corrections treatment that made `word-order` work, and the corpus did
not have enough marked examples.

### Pronouns will not be generated from Vabamorf

`asesonad` is A1, closed-class and looks like the easiest remaining topic —
thirty-five words, decline them, done. Measured, and refused:

```
mina  → genitive "mina"    (correct: minu)
keegi → genitive "kee"     (correct: kellegi)
iga   → genitive "ea"      (that is `iga` meaning *age*, a different word)
```

The short forms `ma`, `sa`, `ta`, `me`, `te` synthesise to nothing at all.
Estonian pronouns are suppletive and Vabamorf's paradigms for them are not
usable as an answer key, so a generated pronoun drill would be confidently
wrong several times a page — the `kool, koola, koola` failure again, in a
place where every item is a word the learner uses constantly.

If it is built, it needs a hand-written table of about thirty words, which is
the same shape as `data/seed_glossary.tsv` and now a proven pattern. It is not
a generation problem.

### Local ASR

The plan called for `faster-whisper` with TalTech's verbatim fine-tune, run
locally so a voice never leaves the machine. What shipped is Cloudflare Workers
AI. That is a real deviation and the privacy note on the speaking screen says
so plainly rather than pretending otherwise. The local route still has the
better privacy story and nobody hosts the model.

### Pronunciation scoring

Deliberately never attempted — forced alignment gives timings, not correctness,
and EKI publishes free exercises. The app links them instead.

### The documentation described a structure that was never built

`docs/app-structure.md` had a top-level `Raamatukogu`, put `Kordamine` inside
`Õppimine`, and listed no `Rääkimine`, `Kirjutamine` or free-practice tab. None
of that matched the app. It was a plan being read as a map, and it had been
that way long enough that its "Built" section asserted `pohivormid` could not
gate — true when written, false since the generator landed.

Rewritten 2026-08-21 from `index.html` and `library.py` rather than from
intent, and it now carries the three things this project keeps needing and not
having written down: **which screens are graded by code and which by a model**
(only two involve a model, and neither decides correctness), **where the modules
overlap**, and **why `Sõnavara` sits where it does**.

Worth knowing for its own sake: `Sõnavara` was *already specified* in that
document — "vocabulary by frequency band, Speakly-style" — before it was built.
It was built frequency-ordered by independent reasoning, which converged, but
the specification was sitting there unread.

### Three of the five word statuses had no writer

`vocab` models five: `õpin`, `tuttav`, `tean`, `eiran`, `teadsin ammu`. Two
were reachable — `õpin` set automatically on the first encounter while reading,
`tean` by the word card's button. The other three were modelled, stored and
counted by the overview, and there was nowhere a learner could click to set
them. Same shape as a measurement with no writer and an endpoint with no
caller, which this project has now met three times in three different costumes.

Fixed for `eiran` and `teadsin ammu` on 2026-08-21: the word card carries
**Pole vaja**, and `POST /api/vocab/known` takes an explicit `status`. `eiran`
is the one a vocabulary list needs and a reader does not — browsing B1 nouns
turns up `riigivisiit` and `seinamaaling`, real words that this learner is not
going to spend a morning on, and without a way to say so they return on every
page and the "still to learn" count never means anything.

`tuttav` is still unreachable, deliberately. It sits between met and known,
which is exactly the granularity LingQ's four levels are reported as being too
fine to judge; the boundary that carries weight here is *settled*, and `tuttav`
is on the same side of it as `õpin`. It stays in the model because removing a
stored value is a migration, and earns its place only if something ever needs
to distinguish "seen twice" from "seen once".

## The four biggest files were split, 2026-09-01

Nothing here changed behaviour; the point was that every change had to be made
in one of four files.

| Was | Is |
|---|---|
| `CLAUDE.md`, 716 lines | 218 lines that route, plus `docs/lessons.md` (the 73 habits, grouped) and `docs/ui-language.md` |
| `eesti/app.py`, 1 975 lines | 79 lines of assembly, plus `eesti/api/` — twelve routers, `deps.py`, `render.py` |
| `eesti/cli.py`, 1 620 lines | `eesti/cli/` — six command groups, each registering its own subparsers, plus `_helpers.py` |
| `eesti/web/index.html`, 3 506 lines | 474 lines of markup, `app.css`, and fourteen ES modules under `web/js/` |
| `eesti/library.py`, 638 lines | 456 lines of shelf, plus `eesti/topiclinks.py` — which texts demonstrate which grammar topic |

Four things were found doing it, none of them by the 1 374 tests that were
green before and after:

- **`cli serve` raised `NameError`.** `cmd_serve` read a bare `DB_PATH` that
  was never imported, so the command every document here tells you to run died
  before reaching uvicorn. `--help` proves the parser, and `serve` is the one
  command the read-only smoke list cannot run because it blocks.
- **`GET /api/vocab` had no test at all** — `POST /api/vocab/known` did. The
  whole `Sõnavara` screen answered 500 for the length of one commit, and a
  browser found it in twenty seconds.
- **Eight dead names.** Six functions in `app.py` with no decorator and no
  caller (the leftovers of six deleted routes), and two constants in `cli.py`,
  one of them a hardcoded `data/notion.db` shadowed by the config import beside
  it.
- **Two page modules were never imported.** `write.js` and `reading.js`
  export nothing anybody calls — they wire their screen's buttons when they
  evaluate — so in a module graph they simply did not run. `Kirjutamine`
  opened, looked complete, and every control on it was dead, with no console
  error. The browser suite caught it; `test_ui_contract` fails on an
  unreachable module now.
- **`eesti/api/render.py` needed `sqlite3` that nothing imported** — inside two
  `except sqlite3.Error` handlers, which would have turned a degradation path
  into a crash. Found by pyflakes, which nothing had run over this code.

### The dead code, and what was decided about each

Five functions had no caller anywhere in the repository — not in `eesti/`, not
in the tests, not in `deploy/` or the workflows. This is the shape this project
keeps meeting, so each got a decision rather than a shrug:

| | |
|---|---|
| `difficulty.band_counts` | **Dropped.** Its docstring said "for the reading view" and the reading view never asked. A four-line `GROUP BY` if it is ever wanted. |
| `harvest/err.fetch_episode` | **Dropped.** A one-line wrapper over `parse_episode(_get(url), url)`; `harvest()` calls those two directly. |
| `notion.from_correction` | **Dropped.** It mapped a `grammar.Correction` to a `Row` and nothing produced one on that path — the page posts flat fields. It also relabelled an unknown tag to `vocab` silently, where `/api/notion/queue` rejects it with a 400, which is the better of the two behaviours and the one in use. |
| `providers/grammar.reset_breakers` | **Dropped.** A one-line wrapper over `breaker.reset()`; the tests call that directly and there is no "retry now" control. |
| `sources.ingest_file` | **Kept, and now wired.** It was the only code that could put a textbook chapter or a tutor's handout into the corpus, with nothing able to call it. `cli ingest <file>` calls it: a JSON array of items, or any text file as one passage. It defaults to a new registry source, `oma-materjal`, marked **not redistributable** — this project cannot know what licence a file dropped into it carries, and somebody else's textbook gets the same posture as HARNO's exam papers. An unregistered source is refused before the file is read, saying what to use instead. |

Two computed values nobody read went with them: `progress.report` called
`mastered(conn)` into a variable it never used, and `readiness._parts` called
`seen_items(progress)` the same way. Both are pure reads; the schema the second
one creates is created again by `exposure()` on the next line, which is why
dropping it is safe and worth checking before doing.

### Three jobs that were written twice

- **`library.browse` and `library.count`.** `count`'s docstring said it was
  "built from `browse`'s own filters rather than beside them" and it was beside
  them — the same three clauses, in the same order, in two functions whose only
  contract is that they agree. One `_filters()` now, and the docstring is true.
- **The verb query.** `conjugation.py` and `verbs.py` each held the same SQL for
  "level-appropriate verbs, most frequent first". It is `wordlist.verbs_at_level`
  now, beside its noun twin.
- **The retrying fetch.** `rection.py` and `harvest/evkk.py` had the same loop
  character for character, with the same constants. It is `eesti/net.py`, which
  has the first tests this logic has ever had. One deliberate difference: it no
  longer sleeps after the *final* attempt, which only delayed the exception.

**All six now go through `eesti/net.py`.** They had three timeouts (45 s, 60 s,
90 s), two retry styles and two User-Agent strings between them, one of which
was no User-Agent at all. Each keeps its own timeout, its own attempt count and
the User-Agent it has always sent — those differ for reasons (paging a whole
WordPress archive is not reading one page), and consolidating *how* a request is
made must not quietly standardise *what each host is given*. A test holds each
of those numbers, and another fails on any module under `harvest/` that opens
its own connection.

The one thing that had to be designed rather than moved is the failure. Callers
already caught two different exception types and both were right: `lihtsad`
catches `OSError` per issue, so one dead URL costs one issue rather than the
run, and the EVKK command catches `RuntimeError` to turn a research host being
down into a sentence instead of a traceback. `net.Unreachable` inherits from
both, so every existing handler still catches — a single base would have broken
one of them silently, on the one day the handler exists for.

The provider calls (`providers/*`, `notion.py`, `cli push-content`) stay
separate on purpose: they are POSTs with a circuit breaker and rate limits to
tell apart, which is a different job, and `docs/lessons.md` has the entry about
a retry there keeping a failure alive.

### Things the code already knew, that nothing had said out loud

Each of these was true, relied on, and written down nowhere. They are the
expensive kind: not a gap somebody forgot to fill, but a fact the code depends
on that no one has to learn until it breaks. Each now has a check.

| The unstated fact | What holds it now |
|---|---|
| **Registration order is behaviour.** `/api/library` and `/api/library/{item_id}` answer correctly because of the order they were declared in — invisible while every route lived in one file. | `test_route_inventory.TestTheOrderThatIsBehaviour` asks the app for both. |
| **The page's single file was doing work.** Every screen's buttons were wired because the code was *in the file*. Split into modules, "these must be loaded" became a claim somebody has to make, and two screens silently stopped being wired. | `test_ui_contract.TestEveryModuleIsReachableFromTheEntryPoint`. |
| **`browse` and `count` must agree.** The docstring asserted it; nothing tested it, and the two filter chains were separate copies. | `test_library.TestBrowseAndCountAgree`, over seven filter combinations. |
| **Two modules must pick the same verbs.** `conjugation.py` chose what to drill and `verbs.py` chose what counts as irregular, from two copies of one query. | `test_conjugation.TestOneAnswerAboutWhichVerbsAreReady`. |
| **A "read" function that writes.** `library.seen_items` runs `executescript(SCHEMA)`; a caller dropping the *value* would have dropped the schema creation too, on any path that ran before `exposure()`. | Written down here; the deletion that prompted it checked first. |
| **`api.ROUTERS` and `cli.GROUPS` cannot be derived** — order is a choice — so they are the two hand-maintained lists this refactor created, in a repository whose most-repeated bug is exactly that. | Both directions checked: every module with a `router`/`register` is in the list, and every entry comes from the package. |

Two more that are recorded rather than enforced, because the check would cost
more than it is worth:

- **The suite's result depends on undeclared local state.** The same command
  reports 1 451 passed, or 1 440 with eleven more skips, or "144 skipped" for
  the browser journeys, depending on whether `data/` holds a built word list —
  which is git-ignored and invisible in the output. A comparison of two runs is
  only meaningful if both had the same `data/`.
- **Vabamorf's first synthesis in a process costs about 1.7 s.** Every timeout
  in the browser suite is implicitly budgeted around that being paid before the
  assertion; under load it is what pushes a 20 s `wait_for_selector` over.

### The checkpoint under-delivered, and the fixture that hid it

`checkpoint.build` promised `count` items and returned however many the first
pass produced. It asked each topic for `count // topics + 1`, dealt every pool
to exhaustion and stopped: against a thin word list A1 asked for 12 and got 8,
silently. A thin word list is not a test artefact — it is what a deployment
looks like before content is pushed, and `/api/checkpoint/{level}?count=15` is
a promise the learner sees as a quiz length. It asks again now, doubling, until
it has what was asked for or nothing new comes back; each pass deals
round-robin, so the no-two-in-a-row interleaving holds across the seam and not
merely within a pass. Cost measured: 9–24 ms once Vabamorf is warm.

The test that caught it had been failing on `main` too, but only in isolation —
it passed or failed depending on what ran before it, which is why adding one
unrelated test file surfaced it.

Behind that was the reason it was invisible: **a full run leaves an empty
`data/eesti.db` behind** — 0 rows, correct schema. `real_wordlist` gated on
`exists()`, so on the *next* run two curated-content tests stopped skipping and
checked Estonian against an empty lexicon. Two failures, in a file nothing had
touched, reading exactly like a regression. The fixture counts a row now
(`wordlist.available`), which is this project's oldest rule written into the
fixture that existed to honour it.

**Found, after three commits of it being open.** It was never the test suite.

`python -m eesti.cli status`, `themes`, `vocab`, `readiness`, `drill`,
`conjugate`, `patterns` and `placement` — typed by a person before
`cli build` — each read the lexicon through `wordlist.connect()`, which creates
the file and applies the schema. So *reading* the word list manufactured one:
zero rows, complete schema, indistinguishable from a real build to anything
asking `exists()`.

Why it took so long is the useful part, and all three reasons are the same
mistake in different costumes:

- **`test_cli_smoke` runs all eight commands, in-process**, where the autouse
  fixture redirects `config.DB_PATH`. A suite that exercised every culprit could
  never show the bug.
- **An in-process `sqlite3.connect` spy cannot see a subprocess.** `PYTHONPATH`
  is inherited; a monkeypatched attribute is not. The hunt is committed as
  `tests/phantom/` — the same audit hook, injected so it loads everywhere.
- **The evidence arrived one run late.** `real_wordlist` gated on `exists()`, so
  the run that created the file was fine and the *next* one failed, in an
  unrelated file, looking like a regression.

Two suspects were eliminated rather than searched. Five full runs under the
subprocess-wide hook recorded **not one read-write open of that path** — so
nothing in `pytest tests/` does it. And the uvicorn subprocess is ruled out by
construction: `live_server` skips when the word list is absent, which is the
only condition in which the file could be created; when it is present there is
nothing to create.

**It reached further than the CLI.** `practice.items_for` — library code behind
`/api/practice`, placement, the checkpoint and the handoff — opened the word
list the same way. On a deployment where content had not been pushed, the first
learner to ask for a drill created a convincing empty lexicon on the server.
That one raises now, and the route already turns it into a 400 carrying the
text; returning no items would have read as "this topic is broken" rather than
"nothing has been built here".

**The fix is a helper that already existed.** `cli/_helpers.words_db` asks
`available()` first and says what to run, and its docstring already called this
"the fourth instance of the same bug". Eight commands bypassed it.

Two guards were themselves defeated by the phantom, both asking existence where
they meant rows:

- `cli serve` refuses to start without a database — and an empty word list
  satisfied `exists()`, so it served the whole app with a zero-word lexicon:
  every drill empty, every lookup missing, no message anywhere.
- `test_e2e_journeys.live_server` gated the same way, so a phantom would have
  unskipped the entire browser suite against an empty lexicon — around 140
  failures that look like a regression and are a missing build.

The regression test asks the property of **every** command in
`test_cli_smoke.READ_ONLY`, derived from that list rather than written again,
as real subprocesses. A source grep cannot express it: `cli build` and
`cli export` open the word list to write it and must keep creating. Writing the
check that way immediately caught five creators beyond the three the manual
hunt had found — including `readiness`, which the hand-run hunt had reported
clean because the argument was typed as `readiness A2` rather than
`readiness --level A2` and argparse rejected it before the code ran.

The conftest guard from the previous commit stays. It is now a trap for the
next instance rather than the only evidence for this one.

### The two Estonian models are wired, and neither is adopted

Both were recorded on 2026-09-01 as existing and left there. An option nobody
can reach is an option nobody can measure, so both now have a lane; neither has
a number, and nothing was reordered in front of an incumbent on the strength of
being new.

**EstLLM, hosted.** `huggingface` is back in `PROVIDERS` — the same lane that
was deleted in August after the probe found the router serving 132 models and
not one Estonian one. It is second in `LLM_PREFERENCE`, directly behind `local`
and ahead of every general-purpose model, and that is the *same* argument
rather than a new one: it runs the same Estonian-adapted weights, on hardware
somebody else owns. `HF_TOKEN` is already this deployment's vocabulary, since
`providers/asr.py` reads it for hosted Whisper.

What is **not** verified: that a request completes. The HF router answers 401
before it routes, so an unauthenticated probe returns 401 for a real id and a
made-up one alike and proves nothing. Only a call with a token settles it, and
this repository must never hold one. `cli eval --provider huggingface` is the
command that turns the lane into a number.

Wiring it uncovered a drifted list. `cli/build.py` held a hand-written
`_PROVIDERS` tuple that had gone wrong in both directions at once: it offered
`huggingface` when no such provider existed, so `--provider huggingface` was an
accepted choice that could only raise `KeyError`; and it omitted `local`, so the
one lane running an Estonian-adapted model was the one lane the eval could not
score — on the command whose whole job is to find out whether a model is any
good at Estonian. It is derived from `llm.PROVIDERS` now. Unlike `api.ROUTERS`
and `cli.GROUPS` it carries no ordering decision, so there was nothing to keep
by hand.

**Voxtral, local.** `TalTechNLP/Voxtral-Mini-3B-2507-estonian`, Apache-2.0,
published 2026-08-25, hosted by nobody (re-probed 2026-09-01). It is an
audio-*understanding* model rather than a Whisper, so whisper.cpp cannot run it
and the prompt is load-bearing — asked nothing in particular it will return a
summary, a subtitle track or a news story, all of which it was trained to
produce from the same recording. It shells out to llama.cpp's multimodal CLI,
because an OpenAI-shaped `/v1/audio/transcriptions` on llama.cpp is an open
feature request rather than a merged endpoint.

It sits **behind** whisper.cpp. Its card reports 5.05 % WER and says in the same
paragraph that the validation set is ten recordings and should not be read as an
estimate of Estonian ASR quality. Nobody has said anything about it — 48
downloads, zero likes, no discussion found — which is itself worth recording,
because "new model, must be better" is the reasoning this project's eval exists
to refuse.

One earlier claim corrected: the note called it "TalTech's Estonian Voxtral with
GGUF builds". TalTech published bfloat16 safetensors only; the quantisations are
`mradermacher`'s. Whoever pulls them is trusting a converter as well as a
trainer.

### Third-party sources, re-probed 2026-09-01

Every endpoint the code actually calls answers: ERR's two archives, HARNO,
EIS's public items, Sõnaveeb (`api.sonapi.ee/v2`), TartuNLP's TTS and
translation (both `/v2`), the Selges keeles WordPress API, EVKK's taxonomy, the
Ekilex word list on GitHub raw, and EKK SÜ 64. No API version has moved; there
is nothing to migrate to.

Two registry URLs answer non-200 and both are fine: the Ekilex *repository
page* is 403 to an unauthenticated fetch while the raw data file it exists for
is 200, and `api.sonapi.ee/v2/` with no word is 404 while `v2/raamat` is 200.
Worth writing down, because "the link check went red" would otherwise be
rediscovered as a problem twice a year.

**The one claim that had gone stale was ours, not theirs.** `docs/local-llm.md`
recorded, correctly, that on 2026-08-20 nobody hosted any Estonian model. On
2026-09-01 the exact model this project pins is served by featherless-ai,
status `live`. Three weeks. The note also said "this is not a gap that is about
to close", which is the sort of sentence that should not be written about
somebody else's roadmap.

Two Estonian models exist now that did not: a 70B EstLLM (2026-08-17, ~40 GB at
Q4 — a bigger machine, not a Mac mini) and TalTech's Estonian Voxtral
(2026-08-25) with GGUF builds, which is the first real candidate for the
speaking lane's recogniser. Neither is measured on this project's eval and
neither is adopted for being new.

### Dependencies, checked 2026-09-01

| | |
|---|---|
| `estnltk` | **1.7.4 → 1.7.5.** The one pin that is an answer key: a drill's correct answer is whatever `synthesize()` returns. Taken only after measuring — 2 600 forms (400 nouns × 4 cases, 200 verbs × 5 forms, A1–B1 by frequency) identical under both, and `cli build` indexing the same 2 416 object cases and 1 671 drillable nouns. Do that again before moving it. |
| `httpx` → `httpx2` | Starlette's TestClient warns on every import that plain `httpx` is deprecated for it. Nothing in `eesti/` imports either — the app's own HTTP is urllib — so this is a test dependency that happens to live in `requirements.txt`. |
| `typescript` | **5 → 7**, verified by running `tsc --noEmit` over `deploy/worker.ts` on 7.0.2: clean. |
| `wrangler`, `@cloudflare/workers-types` | Floors raised to what was installed and tested. Both were already inside their caret ranges, so this records the tested state rather than changing it. |
| GitHub Actions | `checkout@v4 → v7`, `setup-python@v5 → v7`, `setup-node@v4 → v7` — three majors behind, all runtime bumps. CI proves these; nothing else can. |
| `fastapi`, `uvicorn`, `fsrs`, `pytest`, `playwright`, `pydantic` | Already latest. |

**pytest 10 will remove class-scoped fixtures declared as instance methods.**
Seven test files had them; they are `@classmethod` now, and the suite passes
with `-W error::pytest.PytestRemovedIn10Warning`. That was a deprecation with a
removal date, not a style note.

**Python moves to 3.13**, on evidence rather than on the wheel list:

- CI runs a **matrix**, 3.11 and 3.13, `fail-fast: false`. The 3.13 leg passes
  the whole suite *and* the morphology gate against TalTech's native gold
  forms — not merely the unit tests.
- Locally, on a real 3.13.7: `pip install -r requirements.txt`, then the
  image's own pipeline. `cli build` produced the same numbers as 3.11 —
  160 316 words, checked=2575 indexed=2416, 1 671 drillable nouns — and
  `cli export` completed. Vabamorf's compiled extension is the whole risk, and
  it synthesises identically.
- The Dockerfile's two stages are `python:3.13-slim`. 3.11 stays in the CI
  matrix because it is what the image shipped until now.

**Verified on the deployment, 2026-09-02.** The image was not built here — this
container has a Docker CLI and no daemon — so until it shipped, "the deps
install on ubuntu-latest" was all that had been shown, and that is not "the
image builds". It builds. PR #30 merged at 20:11:20Z, Cloud Build produced an
image stamped **20:14:20Z**, and a smoke run against the deployment came back
clean on every check: health, the origin guard, `/api/library`, `/api/status`,
`/api/curriculum`, speech and the reading library. Vabamorf's compiled
extension was the whole risk and it builds and answers on 3.13 in the real
image, not only on a runner.

**One sentence here used to be wrong, and it is worth keeping the correction.**
It said "`deploy.yml` is what will say". `deploy.yml` cannot say: it deploys
the **Worker**, and the app is a container built by a Cloud Build trigger on
`main`. `docs/deploy.md` had this right all along — *"The `deploy` workflow
going green means the Worker is current; it says nothing about the container"* —
so this file was contradicting the file that owns the subject. Anyone reading
it would have watched a green Worker deploy and concluded the 3.13 image was
fine. What actually answers is a **smoke run after the build window**, reading
`image built`.

### The smoke check could not see the deploy it fires on

Finding the 3.13 image required a *manual* smoke run, and that turned out to be
the interesting part.

`smoke` fires on `workflow_run: [deploy] completed`. `deploy` deploys the
Worker; the app is a container built by a Cloud Build trigger on `main`, which
nothing here can observe. So the smoke run that fires on a merge is looking at
the **previous** image — not usually, structurally, every time.

The merge of PR #30 measured it exactly:

| | |
|---|---|
| merge | 20:11:20Z |
| smoke fired, all green | 20:12:11Z — reporting an image built **14:39:50Z**, 5½ hours old |
| the new image actually landed | 20:14:20Z, two minutes *after* that run |

Every check in that run passed, about a deployment that did not contain the
merge. On the one merge whose open question was "does the image build at all",
the automatic answer was a green tick about the old image.

The run had both halves and never put them together: it printed the build
stamp, and `github.event.workflow_run.head_commit.timestamp` was sitting
unused. It compares them now and says **STALE IMAGE — … everything below
describes the PREVIOUS deployment** when the image predates the commit, and
says so out loud in the good case too, because silence on success cannot be
told from never having checked.

A **warning, never a failure**: a stale image inside the Cloud Build window is
the normal and correct state, and a check that failed on every merge is one
people learn to scroll past. It stays silent on a manual dispatch, where
`head_commit` is empty and there is no "the change I just merged" to compare
against. All five branches were driven under `bash -e` against the real
extracted script — `bash -n` has been wrong in this file before.

### `cli placement` wrote fifteen wrong answers nobody gave

Found by asking a question the documents already pose: *has the practice number
moved?* This container's `data/progress.db` held **15 attempts**, all
`kusisonad`, all `correct=0`, all with an empty answer, in three bursts of five
— on a machine where nobody has ever studied.

`cli placement` wrote them. It is in the CLI's own **`READ_ONLY`** list, and
that name is a promise.

One line caused it. `_helpers._ask_terminal` caught `EOFError` and
`KeyboardInterrupt` and returned `""` — and `""` is not "no answer", it is a
**wrong answer**. Every consumer of the `Ask` contract then graded and recorded
items the learner never saw:

| | |
|---|---|
| `cli placement </dev/null` | a whole fabricated failed sweep, 15 attempts |
| Ctrl-C during a sweep | did not leave. `cmd_placement` prints "Ctrl-C to leave early"; the interrupt became a blank answer and the sweep went on marking topics wrong |
| `cli checkpoint` | the same, plus a **failed checkpoint row**, plus every un-shown item pushed into the review queue |

Not cosmetic. Wrong answers fill the accuracy window that gates mastery, and
the checkpoint row feeds the **readiness verdict** — the one that decides
A2-then-B1 against B1-alone in 2027. A record of practice nobody did makes the
learner look worse than they are, which is the direction that costs something.

`placement.Stopped` is the fix: the absence of an answer is its own signal and
it ends the session. An exception rather than a returned sentinel, because a
caller that forgets to check a `None` grades it as wrong, which is the bug
again. `probe` lets it propagate, `sweep` catches it and returns what it
genuinely probed, and `checkpoint.run` deliberately does **not** catch it — an
abandoned checkpoint must not be indistinguishable from "no items could be
built", which is what the empty `CheckpointResult` already means, and `score`
divides by `asked`. Answers given before the stop stay recorded, because those
were real.

**Why 1 500 tests never saw it.** `test_cli_smoke` runs every `READ_ONLY`
command and asserts each exits clean — but in-process, via `cli.main()`, where
the autouse fixture redirects all four learner databases. The promise the list
makes was never tested. Identical blind spot to the phantom word list, and the
same fix: `tests/test_read_only_is_read_only.py` asks the property of real
subprocesses, derived from `READ_ONLY` rather than restated, comparing the
learner's four databases **byte for byte** — a command that added one row and
removed another would pass a row count.

### Most merges deployed with nothing checking the deployment

Found immediately after shipping the staleness warning above, which is the
point: that fix made the smoke run honest about *which* image it saw, and this
is the discovery that on most merges it never ran at all.

Cloud Build rebuilds the image on **every** push to `main`. `smoke` fires on
`workflow_run: [deploy] completed`, and `deploy` is filtered to Worker paths:

```yaml
paths: [deploy/**, wrangler.jsonc, package.json, package-lock.json,
        .github/workflows/deploy.yml]
```

| a merge touches | image rebuilt? | `deploy` runs? | `smoke` runs? |
|---|---|---|---|
| Worker paths | yes | yes | yes — ~1 min later, so it sees the **old** image |
| **anything else** | **yes** | no | **no. Nothing verified the deployment** |

Measured when this was found: **`deploy` had 8 runs against roughly 17 merges
to `main`.** Half the deploys of this app had never been checked by anything.
Two costs already paid — the Python 3.13 image went ten hours unverified after
PR #30, and PR #31, a Python change, produced no smoke run whatsoever.

`smoke` now also runs **daily**, so any merge is checked within a day whatever
it touched. Deliberately not `push: branches: [main]`: that fires within a
minute of every merge, always before Cloud Build finishes, so every run would
warn STALE and the warning would become the thing people scroll past — the
exact failure it was written to avoid.

A scheduled run has no triggering commit, so it asks the API for `main`'s head
and compares against that; a failed lookup warns rather than failing, because
somebody else's bad minute is not this app's outage.

**The two stale cases are diagnosed differently, because they are different.**
Minutes after a merge, an older image means Cloud Build has not finished —
come back shortly. A day later, on the schedule, it means the build **failed or
never ran**, and telling somebody to "re-run in a few minutes" would send them
somewhere there is nothing to find.

**Unverified until it has happened:** that the schedule fires and reports a
post-merge image. That takes a day, and all seven branches were driven under
`bash -e` against the script extracted from the real workflow with a stubbed
`curl` — which is not the same as the cron having run.

### "Erase ALL practice history" cleared two of five tables

`deploy/reset-progress.sh --everything` prints **"This erases ALL practice
history. Type ERASE to confirm"**. Behind it, `progress.reset(conn, None)`
deleted `attempts` and `topic_state` — and `progress.db` has five tables.

The other three are created lazily by the modules that own them, which is why
they were missed: `checkpoints` by `checkpoint.py`, `exposure` by `library.py`,
`dictation` by `dictation.py`. All three are read by the readiness verdict.

Measured before the fix, on a database holding one passed A2 checkpoint:

```
before : {'attempts': 1, 'topic_state': 0, 'checkpoints': 1}
after  : {'attempts': 0, 'topic_state': 0, 'checkpoints': 1}
passed_levels after "erase ALL practice history": {'A2'}
```

So a learner could erase everything and the app still believed they had passed
A2 — and `readiness._parts` gates the whole verdict on `checkpoint_passed`.
Every part of the record that says "you have done this" survived the erase.

The full branch is now derived from `sqlite_master` rather than listing tables:
every table in the learner's progress database *is* learner progress, and a
sixth one added later is covered without anybody remembering to come back. The
list was itself an instance of this repository's most-repeated bug.

**The topic-scoped branch deliberately still touches only its two**, and that is
not the same omission: a checkpoint is level-wide, exposure is per reading item
and a dictation is per sentence, so none can be attributed to one topic.
Clearing them for a topic reset would destroy records the request never asked
about.

Scope kept honest: this is `/api/progress/reset`, so it clears `progress.db`.
The review queue (`review.db`) and the vocabulary table (`vocab.db`) are
separate files and separate endpoints, and widening the route to them would be
a behaviour change rather than a fix.

### The Worker's second lock covered two of five routes

`_require_state_token` says in its own docstring that a restore endpoint "does
not rely on a single layer": Access guards the Worker, the token guards the
route. The Worker's half was `startsWith("/api/state/")` — a naming convention
rather than the set it meant.

Five origin routes require `STATE_TOKEN`. That prefix covered two:

| route | what it does | was blocked? |
|---|---|---|
| `/api/state/export` | reads the learner's databases | yes |
| `/api/state/import` | overwrites them | yes |
| `/api/progress/reset` | **erases practice history** | no |
| `/api/content/import` | **overwrites the corpus** | no |
| `/api/content/export` | reads the corpus | no |

**Never an open door**, and worth being precise about: the origin demands the
token either way, so a request without it gets 403 whichever path it takes.
What was missing is the second layer the design claims to have, on the three
routes where losing the first one costs most.

The block is the explicit set now. A Worker cannot import Python, so it is
hand-maintained — and therefore checked in **both directions** against
`eesti/api/state.py`, the way `api.ROUTERS`, `cli.GROUPS` and `eval.yml`'s
provider list are: every token-guarded route is refused, and nothing is refused
that no route guards. The second direction matters as much: a path 404'd by the
Worker that the origin serves normally is a feature quietly removed from the
deployment while it keeps working under `cli serve`.

The origin half is derived from the source rather than restated, so a route that
starts requiring the token is covered without anybody remembering to come back.

### The vocabulary line on the verdict counted zero, always

`readiness._vocabulary` asked `SELECT COUNT(*) FROM vocab_status WHERE
known = 1`. There is no `known` column: the table is keyed on `lemma` with a
`status`, on the ladder `UNKNOWN, LEARNING, KNOWN, IGNORED, WELL_KNOWN =
0, 1, 5, 98, 99`.

So every call raised `OperationalError`, a bare `except sqlite3.Error` turned
it into `0`, and the readiness screen told a learner who had marked hundreds of
words **"0 из 997 слов уровня"**. Measured: three words marked known through
`vocab.set_status` still produced `{"known": 0, "level_words": 997,
"measured": True}`.

**Two faults, and the second is the worse one.** A wrong column name is a typo.
Reporting the failure as a *measurement of zero* is what kept it invisible —
`measured: True` is the flag the page gates the line on, so the app asserted it
had counted. An unmeasurable part now reports `measured: False` and the line
disappears, which is the rule the rest of that file already follows.

Two things fixed alongside, both of which the old query could not express:

- **`IGNORED` is excluded.** "Ei ole minu jaoks" is a word the learner decided
  not to spend time on; counting it as known would inflate the number with
  exactly the words they skipped. Same set `vocab.bands` uses.
- **It is scoped to the level it names.** The line reads *"N из M слов
  уровня"*. Lemmas live in `vocab.db` and levels in `eesti.db`, so the
  intersection happens in Python; at 997 words for A2 that costs nothing.
  Unscoped, the numerator counted every known word at any level against one
  level's total, which can exceed 100 % and means nothing when it does.

### The corpus half of the object-case drill reached nobody

`cloze.negation_clozes` is the one object-case generator that draws on real
Estonian: under negation the partitive is exception-free, so a harvested
sentence settles the case with no aspect judgement and no risk of marking a
licit answer wrong. It is written, documented, tested, and files its items
under `obj-case`.

It ran nowhere but the CLI. `practice.items_for` dispatches on
`by_id(topic).generator`; the call sat inside the `generator == "corpus_cloze"`
branch behind `if topic == "obj-case"`, and `obj-case`'s generator is
`object_case`. The two conditions could never both hold, so the branch was
unreachable — on the topic this file calls the documented #1 weakness, whose
practice was therefore twelve hand-written frames and nothing else.

Nothing failed, which is why it survived: the `object_case` branch further down
answered every request perfectly well.

`obj-case` sets are now blended — up to `practice.CORPUS_SHARE` (a third) of
the items come from the corpus, the frames supply the rest and still carry the
completed/ongoing contrast that a corpus sentence leaves implicit. The corpus
stays optional: without a `content.db` the templates fill the whole set, so a
deployment that has not had `deploy/push-content.sh` run loses nothing it had.

The guard is derived rather than written out: `tests/test_cloze.py` parses
`items_for` and asserts, for every `topic == "x"` inside an
`if generator == "y"` block, that `curriculum.py` agrees the two go together.

### `HF_TOKEN` — the tutorial exists now

The EstLLM lane has been "wired but unmeasured" since 2026-09-01 for one
reason: this repository must never hold a token, and the HF router answers 401
before it routes, so nothing here can prove a request completes.
`docs/hf-token.md` is the procedure that closes it from the outside — where to
get a token, which of the three surfaces (Cloud Run, Actions, `.env`) needs it,
and the command that turns the lane into a score. Until somebody runs step 3,
this stays unmeasured, and this paragraph says so on purpose.

### The eval scored a prompt the app does not ship

`evals/gec.py` carries a comment recording the failure its prompt was built to
fix: on the first real run a model flagged **four of eight already-correct
sentences**. The fix was three mechanisms — rules stated positively, worked
examples that include correct sentences, ambiguity resolved toward silence.

All three went into the eval's prompt. `providers/grammar.py` — the prompt the
learner actually meets — carried one line of it (*"Do not invent errors"*). The
two had drifted on precisely the axis the eval measures, so a good eval score
was a score for a different prompt, and the production prompt's real behaviour
on already-correct Estonian was never measured at all.

The object-case rules and the say-nothing instruction are now in both, lifted
verbatim rather than paraphrased. The worked examples are deliberately **not**
copied across: the production contract has a fourth field (`why`, in Russian)
that the eval's three-field examples would contradict.

`tests/test_provider_chain.py` holds the shared half in both and asserts the
halves that must differ still differ — a guard that could be satisfied by making
the two prompts identical would break what it was written to protect.

**Not yet verified:** that this improves the production checker. The change
lengthens the prompt the learner meets, and the honest test is the eval set run
against both prompts on one lane. That has not happened, and this paragraph says
so rather than implying it has.

### A lane was sent a parameter its own model rejects

`providers/llm.py` put `temperature: 0` on every request to every lane.
Sampling parameters are **removed** on `claude-sonnet-5`, the model this file
pins for its own `anthropic` lane, and return 400 on Anthropic's native API.

Nothing was failing: that lane has no key set and sits last in `LLM_PREFERENCE`.
It is the shape of a fault caught before it fires — and the same shape that cost
a day on the `huggingface` lane, where a parameter no provider supported came
back as `model_not_supported` and sent the diagnosis to the model id.

Fixed with the per-provider capability flag that lane already established:
`Provider.sampling`, false for `anthropic` only. `temperature: 0` stays
everywhere else — grading here is deterministic, and the flag exists to stop a
lane being sent what it refuses, never to make an answer less repeatable.

## Known bugs and rough edges

Nothing here is severe enough to block use. All of it is real.

| | |
|---|---|
| ~~**`_bind_breaker()` runs at import**~~ | **Fixed 2026-08-20.** `breaker.bind_later(progress_db)` registers an opener instead of a connection, and the breaker opens it the first time it has something to remember. Importing `eesti.app` now opens no database at all, which is asserted. The conftest workaround that dropped the binding is no longer load-bearing. |
| ~~**`wordlist.connect` invents an empty database**~~ | **Fixed 2026-08-20**, exactly as this entry proposed: `wordlist.available()` opens read-only and counts a row, and `cli.words_db()` is the twin of `cli.content_db()` — it declines with "run `cli fetch-data` and then `cli build`" instead of handing back a convincing empty database. `connect` still creates, because `cli build` must be able to. |
| **`sonapi`'s raw payload cache is ephemeral** — *and that is correct* | Re-examined 2026-08-20 and **downgraded from a bug**. Every path that can reach Sõnaveeb from the running app goes through `gloss.remember`, which is durable and in the snapshot; `sonapi.entry_url` builds a string and touches nothing. The only caller of the file cache is `cli rections`, which runs **in the Docker build**, where a cache that lives for one build is exactly right. Nothing re-requests anything on a cold start. Left alone deliberately rather than moved for tidiness. |
| **The local `content.db` is partial** | 349 Selges keeles items only. The ERR transcripts, news issues and exam pointers were lost to a container rollback and not re-harvested. The **deployed** database is the complete one; the last smoke run confirms `"library":true`. Re-run the harvesters before trusting local numbers about the corpus. |
| **The container rolls the checkout back** | Twice in one session, once taking a committed-but-unpushed commit, and once reverting a session that had already pushed — leaving `origin/main` pointing at `Initialise repository` while GitHub held the full history. Nothing was lost either time, but a local `git log` is **not** evidence about the repository. `git ls-remote origin` is. Recover with `git fetch origin --prune && git reset --hard origin/<branch>` — **and then rebuild the derived artefacts**. The rollback also restores a stale `data/edge.db`, which presents as two failing export-quality tests (`kool` still carrying `koola, koola`) that look exactly like a code regression and are not one: CI passes on the same commit because it builds the dataset fresh. `python -m eesti.cli export` fixes it. |
| **The grammar checker is in offline mode on the deployment** | Found 2026-08-20 by the deep smoke check, after the v1.0 image shipped. The chain reports `llm:openrouter: HTTPError` — the key *is* on the process and the call fails, which is a different problem from `unavailable`. Writing still flags object-case candidates and typos, but no correction carries an explanation, so no "log it" button renders and **nothing reaches the Notion log**. Same inert chain as the original key-on-the-Worker bug, from a different cause. PR #18 makes the note name the status code, which decides whether it is a 429 (self-healing) or a 401 (needs a new key on Cloud Run). |
| **`evkk` reaches the network** — now fails like a citizen | Still one live request, and still excluded from the suite: it fetches from `elle.tlu.ee`, and a suite that depends on a research host is a suite that goes red on somebody else's Tuesday. **Fixed 2026-08-20:** it no longer dies with a traceback when that host is down. It says what happened, names the cache path a saved copy can be dropped at, and returns 1. A parse that yields nothing is reported too, rather than writing an empty taxonomy over a good one. |

## Tech debt, stated as debt

- **The harvesters' fetch halves are untested**, by choice: a suite that
  re-crawls ERR on every run is a suite that hammers someone else's server.
  Their *parsers* are covered. The line is drawn at the network boundary and
  that is where it should stay.
- **`providers/llm.py` and `providers/asr.py` sit at 67 % and 72 %** for the
  same reason. Going further means mocking HTTP for its own sake.
- **The CLI is 52 %.** The uncovered half is the write and network commands —
  harvest, push-content, notion --push, eval, models, rections, serve. Every
  read-only command runs in the suite.
- **`Cloze` still overrides `hint` and `label`.** Legitimate — for rection the
  case *is* the question — but it is the last place an item class differs from
  the mixin, and worth re-checking if a fifth generator appears.
- ~~**Two `_state_paths()` writers use `write_bytes`** on paths read from module
  globals.~~ **Fixed 2026-08-20**, and it was not as harmless as this entry
  said. `app.py` kept its own copies of the four learner paths, bound at
  import, and both `_state_paths()` and the database helpers read them — so
  redirecting one name without the other pointed a restore at a file the app
  never opened. Everything resolves `config` at call time now, twelve test
  redirects were paired up to match, and two tests pin it: the snapshot and the
  helpers must both follow a redirect of `config` alone.

## Coverage, for what it is worth

**81 % overall**, 5 458 statements. Chased deliberately during this build and
stopped deliberately: it found nine real defects, and the number itself was
never the goal.

Sixteen modules are at 100 %, including every one touched by a defect this
round — `export.py`, `env.py`, `item.py`, `overview.py`, `progress.py`,
`review.py`, `harvest/clean.py`, `config.py`, `grammar.py`, `handoff.py`,
`mining.py`, `speaking.py`.

Everything below 90 %, and why:

| | | |
|---|---|---|
| `evals/fetch.py` | 0 % | downloads benchmark datasets; nothing else in the app calls it |
| `evals/external.py` | 47 % | eval tooling, exercised by CI's separate `eval` job |
| `eesti/cli/` | 52 % | the uncovered half is the write and network commands; every read-only one runs in the suite |
| `harvest/selges.py`, `harvest/err.py` | 57 %, 59 % | parsers covered, fetchers deliberately not |
| `providers/llm.py`, `evals/gec.py`, `providers/asr.py` | 67–72 % | network clients |
| `rection.py`, `harvest/evkk.py`, `harvest/lihtsad.py`, `providers/tts.py` | 80–84 % | network at the edges |
| `providers/grammar.py`, `sources.py`, `wordorder.py`, `eesti/api/`, `providers/sonapi.py`, `difficulty.py`, `readiness.py` | 86–89 % | error paths and degradation branches |

The rest sits at 90 % or above. `wordlist.py` finished at 94 %, `gloss.py` at
99 %.

## What to do first in the next sprint

**Done since this list was written:** the redeploy. It was item 1 — the running
image predated the export fixes, so the deployed word card still printed
`kool, koola, koola` and 319 other invented paradigms. PR #17 merged at 12:21
on 2026-08-20 and Cloud Build had the new image serving by 12:24, confirmed by
the build stamp on `/api/health` rather than assumed from a green workflow.

1. ~~**Run the deep smoke check and read the status code.**~~ Answered
   2026-08-22, run #27 against the live deployment: **429**. The key is alive,
   the free tier is spent, and it recovers on its own — so neither waiting nor
   rotating it was ever the question, and nothing needs doing.

   Two things the run showed that the question did not ask. `grammar explains
   ........ OK` printed in the *same run* where the deep check reported
   `vabamorf-offline`: `/api/engines` reads configuration and says so in its
   own docstring, so a provider with a spent quota answers `can_explain: true`
   and cannot explain anything. That contradiction cost a debugging round once
   before; the cheap check says "configured (live call unproven)" now.

   And the chain has no redundancy to fall back on — `groq`, `workers-ai` and
   `anthropic` are all `unavailable`, meaning no key. One 50/day free tier is
   the whole grammar checker. **A second provider key is the highest-value
   operator action available**, and it is an operator action: no code change
   would help, and a credential must never come through this session.
2. **Re-harvest locally** so `content.db` is whole again and local measurements
   mean something. Still open, and now measured: local holds 349 Selges keeles
   texts and **nothing else** — no ERR radio, no Lihtsad uudised, no HARNO, no
   EIS. Any local number about the library is a number about one source.

   `cli link-topics` was also overdue and has been run: `topic_items` went
   from **0 rows to 470**, which is the join `/api/practice` returns as the
   `reading` beside every drill. Nothing runs it automatically — not a harvest,
   not a deploy — so `push-content` now warns when a corpus has items and no
   links, and names the command that fixes it.
3. **Study.** Counted on 2026-08-22: **7 attempts, all on one topic**
   (`osastav`, 6 correct), 3 items in the review queue, 17 words with a status.
   That is the entire practice history behind 36 topics, 160 316 words, a
   349-text library, 1 400-odd tests and eight merged pull requests.

   This has been item 3 through four sprints. Every one of those sprints
   shipped code and none of them moved this number, and the reason is that
   nothing in this list *can* move it — it is the only item whose bottleneck is
   not the software. The verdict's A2 numbers (no exam part touched, 0 of 7
   topics mastered, checkpoint unattempted) are what decide A2-then-B1 against
   B1-alone in 2027, and they are inputs the app records rather than outputs it
   produces.

   **The honest conclusion for whoever picks this file up next: the app is not
   short of features.** It is short of use. A tenth feature is easier to build
   than a first hour of practice and is worth considerably less, and four
   sprints of evidence now say so. Before adding anything, check whether this
   number has moved; if it has not, the right change is probably none.
4. ~~**Build the vocabulary browser.**~~ Done 2026-08-21 — `Sõnavara`, by CEFR
   level and part of speech, commonest first.
5. ~~**Say the empty-topic message in Russian.**~~ Done 2026-08-21, and it is a
   200 with a reason rather than a 400 carrying an exception.
6. ~~**Put the interface in a language the learner reads.**~~ Done 2026-08-21.
   Labels and grammar terms stay Estonian and carry a Russian gloss; everything
   that explains, warns or instructs is Russian — including the states a
   screenshot never reaches, which is where most of it was hiding: drill and
   dictation verdicts, review grading, empty states, error banners, `aria-label`s
   and the server-side `detail` messages that surface in the banner. The rule is
   enforced by a derived check rather than a list of forbidden strings, because
   the list had an entry that was never in the code and passed for months.
7. ~~**Make the interface answer when it is touched.**~~ Done 2026-08-21.
   Cards lift on hover, tabs take the accent, and the five path states are
   told apart by colour and by shape instead of sharing one grey. The pass
   found four things that were not cosmetic: `mastered` and `in progress`
   reached the screen as raw English, two CSS rules read custom properties
   that have never existed (one of them the rule colouring finished topics),
   the Russian gloss on `Kontrolli` and `Harjuta` was destroyed by the first
   click, and `[data-theme]` was read by the stylesheet with nothing anywhere
   able to set it.
8. ~~**Give spacing a scale and the navigation a shape.**~~ Done 2026-08-21.
   Eleven hand-chosen vertical margins became a six-step scale; the
   `margin-top:0` idiom became one `:first-child` rule, which restored four
   gaps where the idiom had been copied onto elements that were not first.
   Skills and modes are told apart by form — outlined filter pills against a
   segmented switch — with a mark for each of the eighteen destinations, a
   Home control, and a press that moves. Three regressions found by measuring
   rather than looking: a top-level element broke the desktop grid, a flex
   parent moved a gloss from under its label to beside it, and a test scoped
   itself to the head and passed on nothing.
9. ~~**Give a word with no grammar to teach somewhere to go.**~~ Done
   2026-08-21, after looking at `estly.ee` (see `docs/content-sources.md`).
   31.3 % of A1–B1 words have identical genitive and partitive and were being
   refused with "pole midagi harjutada"; they get a `kind="vocab"` meaning card
   now — the kind `review.py`'s schema declared and nothing had ever written —
   rendered as a flashcard with a reveal step, because rating recall before
   seeing the answer makes `Teadsin` a guess about a guess.
10. **The 11 topics that still have no generator.** `eitus` and `pohivormid`
   were the two named here and are built. Of what is left, none is A2 exam
   material in the way those two were, so this is now a genuine "if more is
   wanted" rather than a gap.
11. ~~**Decide whether five word statuses are four too many.**~~ Decided
   2026-08-22: **four rungs, and the question was the wrong shape.**

   The code never compares a status against five values. It uses two
   thresholds — `>= 1` for *met* in `difficulty`, `>= 5` for *settled* in the
   vocabulary list — so the number of named rungs costs nothing structurally.
   And what LingQ's users complain about is being made to *choose* among four;
   here the learner only ever chooses among the three settled ones, because
   `LEARNING` is assigned by meeting a word rather than by judging it.

   What was actually wrong was one rung: `FAMILIAR` (3, `tuttav`) had **no
   writer at all**, no stored rows, and a single reader that ORed it with a
   value that is written. It is gone. The three settled values stay — "I know
   this", "I knew this long ago" and "this is not for me" are different facts,
   each with an input path.

   `tests/test_vocab.py` now asserts every named rung round-trips through a
   named writer, because this was the fourth unreachable value found in four
   sprints.
