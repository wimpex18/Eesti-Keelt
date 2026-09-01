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

**The phantom's creator is not pinned.** It is intermittent, predates this
work, appears in no single test file run alone, and an in-process
`sqlite3.connect` spy never catches it — which points at a subprocess, though
importing the app in one does not reproduce it. Making the gate honest closes
the failure it causes either way; finding the writer is still open.

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

**What is still unverified, and only a deploy can check:** the image itself was
not built here — this container has a Docker CLI and no daemon. The wheel is
`manylinux_2_28`, which Debian slim satisfies comfortably, and CI installs the
same requirements on 3.13; but "the deps install on ubuntu-latest" is not "the
image builds". `deploy.yml` is what will say, and the smoke check after it.

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
