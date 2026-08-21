# Where version 1.0 stands

Written 2026-08-20 at the close of the first build, and revised the same day
after the deployment was actually asked how it was doing. This is the honest
inventory: what works, what was never built, what is knowingly broken, and what
the original research plan promised and did not deliver.

Read `roadmap.md` for *why* things were chosen and `CLAUDE.md` for the habits
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

49 API routes, every one with a caller — `test_route_inventory.py` fails on one nothing can reach. 1 309 tests: 1 244 in-process and 65 browser journeys.

## What a learner still cannot do

Measured 2026-08-21 against the running app, not inferred from the code.

### There is no way to browse vocabulary

`/api/lookup/{word}` and `/api/enrich/{word}` take a word you can already
spell. Nothing answers *"show me the B1 nouns I have not met"* or *"show me the
words for this topic"*. The data for it is all present and already paid for —
160 316 words, CEFR tags on 9 951 of them, `vocab.db` recording every word the
learner has met, and Russian glosses in the gloss store — and the word card
that would display an entry is built and working. What is missing is the list:
one endpoint that selects by level or topic, and a screen to show it.

This is the largest user-visible gap in the app. Every competitor named in the
research has it, and it is the feature that turns a 160 000-word dataset into
something a person can work through.

### The 13 empty topics answer in English, pointing at a developer document

Practising `tahestik` returns:

    'tahestik' has no generator — see step 2 of docs/curriculum-plan.md

The learner reads Russian; `docs/curriculum-plan.md` is not on their machine
and would not help if it were. `sonajark` gets this right in the same
situation — *"Для этой темы нужен текстовый корпус…"* — so the app already
knows how to say it. Same rule as the readiness verdict and the pronunciation
caveat: a message nobody can read is not a message.

### The PWA installs and then needs the network

`manifest.webmanifest` is served and the app is installable, but there is no
service worker, so an installed copy still fails without a connection. Half of
a claim is worse than none of it — the offline core exists (drills, grading and
the wordlist need no network by design) and nothing lets a learner reach it
from an installed app.

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
- **`cli.py` is 52 %.** The uncovered half is the write and network commands —
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
| `cli.py` | 52 % | the uncovered half is the write and network commands; every read-only one runs in the suite |
| `harvest/selges.py`, `harvest/err.py` | 57 %, 59 % | parsers covered, fetchers deliberately not |
| `providers/llm.py`, `evals/gec.py`, `providers/asr.py` | 67–72 % | network clients |
| `rection.py`, `harvest/evkk.py`, `harvest/lihtsad.py`, `providers/tts.py` | 80–84 % | network at the edges |
| `providers/grammar.py`, `sources.py`, `wordorder.py`, `app.py`, `providers/sonapi.py`, `difficulty.py`, `readiness.py` | 86–89 % | error paths and degradation branches |

The rest sits at 90 % or above. `wordlist.py` finished at 94 %, `gloss.py` at
99 %.

## What to do first in the next sprint

**Done since this list was written:** the redeploy. It was item 1 — the running
image predated the export fixes, so the deployed word card still printed
`kool, koola, koola` and 319 other invented paradigms. PR #17 merged at 12:21
on 2026-08-20 and Cloud Build had the new image serving by 12:24, confirmed by
the build stamp on `/api/health` rather than assumed from a green workflow.

1. **Merge #18, then run the deep smoke check and read the status code.** The
   grammar checker is in offline mode on the deployment right now. A 429 means
   the free tier is spent and it recovers on its own; a 401 means the key is
   dead and every writing check stays unexplained until it is replaced. Until
   the code is known, neither waiting nor rotating the key is justified.
2. **Re-harvest locally** so `content.db` is whole again and local measurements
   mean something.
3. **Study.** The verdict's three numbers for A2 — no exam part touched, 0 of 7
   topics mastered, checkpoint unattempted — do not move on their own, and they
   are what decides A2-then-B1 against B1-alone next year. This is the item
   that has been at number three through two sprints while the code around it
   got better; the app now has more features than it has practice history.
4. ~~**Build the vocabulary browser.**~~ Done 2026-08-21 — `Sõnavara`, by CEFR
   level and part of speech, commonest first.
5. ~~**Say the empty-topic message in Russian.**~~ Done 2026-08-21, and it is a
   200 with a reason rather than a 400 carrying an exception.
6. **The 11 topics that still have no generator.** `eitus` and `pohivormid`
   were the two named here and are built. Of what is left, none is A2 exam
   material in the way those two were, so this is now a genuine "if more is
   wanted" rather than a gap.
7. **Decide whether five word statuses are four too many.** LingQ ships four
   and its users report that as already hard to judge; only the *settled*
   boundary is load-bearing here. Cheaper to resolve before anything else
   reads the ladder.
