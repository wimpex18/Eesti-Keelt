# Eesti-Keelt — working notes for a new session

Estonian A2/B1 exam preparation, built for one learner. Read `docs/` for the
reasoning; this file is what a fresh session needs in the first minute.

## Where things stand

**Version 1.0 closed 2026-08-20.** `docs/status.md` is the inventory: what
works, the 13 curriculum topics with no generator, the known bugs, the tech
debt, and what the research plan promised and did not deliver. Read it before
planning a sprint.

**No exam is booked.** The 2026 A2 rehearsal was declined in favour of another
year of study; the sitting is planned for 2027, A2-then-B1 or B1-alone, and
`readiness.TARGET` is `None` until one is chosen. Do not reintroduce a
countdown to a date nobody has picked.

## What this is

A **learn → practise → check** loop, not a checker. Drills are *generated* from
a word list and a morphological analyser, not stored, so practice is unlimited
and every answer is gradeable without a network call.

The documented #1 weakness is `obj-case` — genitive vs partitive for completed
objects. Much of the design points at it.

## The one property that must not break

**Generation and grading are deterministic. No model decides whether an answer
is right or what to practise next.** A model is allowed to do exactly two
things: explain a correction in prose, and say what it heard in a recording.
Everything else — drills, grading, the study order, the mastery gate — is code.
See `docs/ai-boundaries.md`.

## Which language a string is written in

The learner is a **Russian speaker learning Estonian**. That single fact decides
every user-facing string, and getting it wrong is not cosmetic.

| Kind of text | Language | Why |
|---|---|---|
| UI labels — `Kirjutamine`, `Kuulamine`, `Rada` | **Estonian** | the interface is itself exposure, and these are the exam's own words |
| Grammar terms — `osastav`, `omastav`, `täisminevik` | **Estonian** | they must be learned; a translation would have to be unlearned |
| Everything explaining, warning, or justifying | **Russian** | this is where comprehension has to win |
| Estonian example sentences and drill content | **Estonian** | it is the material |

**The rule that makes it concrete: a caveat nobody can read is not a caveat.**
Two strings in this app exist to stop the learner drawing a wrong conclusion —
the pronunciation comparison ("a miss may be the recogniser, not your mouth")
and the readiness verdict ("this is not a prediction"). Both were written in
Estonian, and in Estonian they did the *opposite* of their job: the person they
protect could not read them, so a low score read as "my pronunciation is bad"
and a verdict read as a forecast.

When a Russian sentence names an Estonian concept, keep the Estonian word and
gloss it once: *"Говорение (rääkimine) оценить нельзя"*. That teaches the term
instead of hiding it.

**Done so far:** the readiness verdict and its reasons, the pronunciation
caveat, `library.SECTIONS` descriptions, the source notes on official material,
and the published integration map.

**Still Estonian or English** (audit 2026-08-19): the web UI's own body copy in
`eesti/web/index.html` and `docs/*.md`. Nothing in `data/` needs translating —
it is the study material.

## The three sections

Everything the learner does answers one of three questions, and every library
section belongs to exactly one (`library.MODES`):

| Mode | The question | What lives there |
|---|---|---|
| `oppimine` | "what am I learning today?" | generated drills, Selges keeles, the live ERR news feed, radio courses |
| `kordamine` | "what am I forgetting?" | the FSRS queue, failed items, official consultation workbooks |
| `eksam` | "am I ready?" | readiness verdict, annotated sample performances, official tasks, EIS, intro videos |

Sections filter on **skill and purpose** (`meta.kind`), not skill alone. Skill
alone held only while everything was reading or listening practice; the official
material broke it, because HARNO publishes samples, videos and workbooks that
carry the same skill as a task while being a completely different activity.
Twenty-five items ended up in no section at all — present in the database,
absent from the app, silently. `tests/test_sections.py` has the orphan check
that would have caught it.

## Two scales, never one

A text carries **two different claims** and they must not share a column:

| Field | Means | Who has it |
|---|---|---|
| `level` | CEFR — A2, B1, B2, C1 | only official HARNO / EIS material, where the exam board said so |
| `band` | difficulty relative to its own source — `kergem` / `keskmine` / `raskem` | all harvested prose |

They lived in one column, and a learner filtering `B1` got only exam material —
349 reading texts and 20 news issues invisible to the one filter anybody uses.

**Do not derive CEFR from vocabulary coverage.** It was tried: 342 of 349
deliberately-simplified news items came out as B2, because only 6.2 % of the
160 316 lemmas carry a CEFR tag at all. The scale is not calibrated and no
threshold on it can be.

What *is* computable is **comprehensibility for one learner** — the share of a
text's lemmas that learner has met (`difficulty.comprehensible`). That is the
mechanism the reading research actually names: input works when it is
understood, and understanding is gated by known vocabulary. `/api/reading/next`
ranks by it and puts the instructional band first, because that is where a text
teaches rather than bores or defeats.

It is vocabulary coverage, not comprehension, and the field names say so.

## Where it runs

| Half | Where | Why |
|---|---|---|
| the app | Google Cloud Run | needs Vabamorf, a compiled C++ Python extension |
| the front door | Cloudflare Worker + Access | one hostname, one login, Workers AI for speech |

Both on free tiers. `docs/deploy.md` has the whole picture, including why it is
not a Worker and not a Cloudflare Container.

**Two doors, two locks.** Access guards the Worker. `PROXY_TOKEN` guards the
Cloud Run origin, because Cloud Run must allow unauthenticated invocations to
be free and its `run.app` URL answers the whole internet. The Worker refuses
anything without an Access identity; the app refuses anything without the token.

## What a session can and cannot reach

Working through this repo, you **cannot read the deployed app**: Access blocks
the Worker and `PROXY_TOKEN` blocks the origin. That is correct and deliberate.

- To verify the deployment, run the **`smoke` workflow** (`.github/workflows/smoke.yml`).
  It authenticates with a Cloudflare Access service token held in Actions
  secrets, so the credential is never in a chat or an environment.
- To verify the UI, **run the app locally and drive it with Playwright**.
  Chromium is at `/opt/pw-browsers/chromium`. This is not optional polish: the
  overlapping-navigation bug in `tests/test_web_layout.py` was invisible to 500
  passing tests and obvious in a browser in one screenshot.
- Operator actions on the deployment run **in Google Cloud Shell**, via the
  scripts in `deploy/`, which read the tokens out of the running service so no
  person ever handles them.

**Never** put a credential in a chat message, a commit, or the Claude
environment-variables box. Secrets belong in GitHub Actions secrets (CI),
Cloudflare Worker secrets (production), Cloud Run environment variables (the
origin), and a git-ignored `.env` (local).

## Licence rules that are not negotiable

- **HARNO / EIS exam material** — © Haridus- ja Noorteamet. Indexed as
  *pointers only*; `body` is empty and a test asserts it. Never copied, never
  redistributed.
- **ERR transcripts** and **Selges keeles** — owner-only, `redistributable = 0`,
  behind Access. Roughly 421 items.
- **Sõnaveeb must never be batch-scraped.** `sonapi` is single-lookup only,
  throttled to one live request a second under a lock, and deliberately has no
  bulk helper. Where more than three fields are wanted, **link to Sõnaveeb**
  (`sonapi.entry_url`) rather than fetching more — the same posture as HARNO.
  Answers are kept in `vocab.db` (`eesti/gloss.py`) so a word is asked about
  **once, ever**, capped by `DAILY_BUDGET` per day; the store is one learner's,
  behind Access, never redistributed. Ekilex is CC-BY-4.0, so the copy is
  permitted — the restraint is about their server, not their licence.
- `data/*.db` and `data/exam/` are git-ignored. Runtime databases are never
  committed.

## Commands worth knowing

```bash
python -m eesti.cli serve            # local app on :8000
python -m eesti.cli harvest          # ERR language archives
python -m eesti.cli harvest-reading  # Selges keeles
python -m eesti.cli harvest-news     # ERR Lihtsad uudised — the live feed
python -m eesti.cli harvest-exam     # official EIS tasks (pointers)
python -m eesti.cli link-topics      # which texts demonstrate which topic
python -m eesti.cli notion           # queued errors; --push writes to Notion
pytest tests/ -q                     # 1 141 tests
```

`deploy/setup.sh`, `deploy/push-content.sh`, `deploy/reset-progress.sh` all run
in Cloud Shell and discover the project, service and region themselves.

## Habits this codebase has earned the hard way

- **A measurement without its writer measures nothing.** Three times now: the
  vocabulary table nothing ever wrote to, the snapshot restore that always
  refused, and `/api/library/{id}` reading without recording. When you add a
  reader, find the writer; when you add a writer, check something calls it.
- **Presence of a database is not presence of data.** Two separate bugs came
  from checking that a file existed: the first request creates it *with its
  schema*, so an empty deployment looked full. Count rows.
- **Resolve paths at call time, not at import.** A module-level constant cannot
  be pointed anywhere else, and three bugs in a row came from that.
- **A third party being down must never fail the build.** EKI, HuggingFace and
  EIS are all optional at build and test time, loudly.
- **Never hand-maintain a list of things that already exist somewhere.**
  `TABS` was a literal list of the panel names and it drifted from the panels
  themselves: three of ten were missing, so one panel never hid and two never
  showed. Nothing failed — every click still produced *a* panel. Derive the
  list from the thing it describes, and if it cannot be derived, test that the
  two sides correspond in **both** directions.
- **A true sentence goes stale silently.** The speaking screen promised the
  recording never left the device. That was true; then recognition moved to
  Cloudflare and the sentence stayed, sitting under a second notice that said
  the opposite. Claims about privacy, cost and provenance are facts about the
  code — pin them with a test that fails when the code changes.
- **Check production by asking it.** Three bugs were found that way after the
  full suite was green — and a fourth: the grammar checker running in offline
  mode with the key apparently set.
- **Never give a summary field the same name as a per-item field.** The check
  read the response with `grep -q '"explains":true'`. Every engine in the list
  carries `explains`, and it is true for each LLM provider whether or not that
  provider is available — so the grep matched an unavailable one and reported
  the chain healthy while production was in offline mode. It also contradicted
  a second check in the same run, and a whole round went into diagnosing a
  traffic split that did not exist. The field is `can_explain` now, and the
  workflow reads JSON with `jq`, not with pattern matching.
- **A configuration check cannot see a call that fails.** `can_explain` was the
  fix for the `explains` grep above, and it is a correct field honestly read —
  and on 2026-08-20 it still printed `grammar explains ........ OK` while the
  deployed chain was falling through to `vabamorf-offline` on every request.
  Renaming fixed the ambiguity; it could not fix the category. The field
  reports that a key is on the process, and no field of that kind can report
  that the provider answers. Only sending one real sentence does, which is what
  the `deep` input exists for. Two checks in one run disagreeing is the signal
  — and the first instinct, last time, was to invent a traffic split rather
  than doubt the cheaper check.
- **The local checkout is not evidence about the repository.** The container
  rolled this working tree back twice: once taking a committed-but-unpushed
  commit, and once leaving `origin/main` pointing at `Initialise repository`
  with one commit in it, hours after the real history had been pushed. Both
  times a local `git log` described a repository that did not exist, and the
  second time it nearly produced a confident report that a committed document
  had gone missing. `git ls-remote origin` is the truth; recover with
  `git fetch origin --prune && git reset --hard origin/<branch>`.
- **`bash -n` is not a syntax check.** It passed a condition that parsed at
  runtime as a command substitution and tried to execute a comparison. It also
  cannot see that `[ x -gt 0 ] && n=$((n+1))` ends the step under `bash -e`
  when the count is zero. Run the shell you are shipping — against a stub if
  the real thing is not reachable.
- **State that protects against restarts must survive one.** The provider
  circuit breaker kept its failure counts in a module-level dict. Cloud Run
  scales to zero, so every study session got a fresh process and an empty
  breaker — and with a threshold of two, the first two requests of every
  container lifetime paid a dead provider's full timeout. The thing it existed
  to prevent was the thing it did.
- **A path opened inside a function cannot be redirected by its caller.** The
  readiness verdict opened the Notion queue from `app.NOTION_DB`, so a test
  with its own fixtures read the developer's real data and the suite reported
  differently locally than in CI. Pass the connection; never reach for a
  module-level path.
- **Check the contract in both directions.** `test_ui_contract.py` had asked
  "does every endpoint the page calls exist?" since it was written, and never
  "can every section the API serves be reached?". 82 items — 13 % of the
  library — were indexed, sectioned, API-tested and unopenable. A one-way
  contract test finds typos; it does not find things nobody wired up.
- **The same job written twice becomes two behaviours.** Four harvesters each
  had a private `_TAG_RE`; on one line of input they gave three answers, and
  every difference reached the learner — undecoded entities in 27 000 words of
  transcript, two words joined into one, and a space before every full stop
  that the punctuation drill then showed as correct. The copies were the bug,
  not any of the three symptoms.
- **A rule in a docstring is not a rule.** `sonapi.py` said "single lookups
  only" because Sõnaveeb asks not to be batched. Nothing stopped a loop. It is
  a one-second minimum between live requests now, and cache hits stay free —
  under a lock, because a sync FastAPI route runs in a threadpool and two
  unlocked readers would both see the same stale stamp and fire together.
- **A cache that protects someone else must outlive a restart too.** `sonapi`
  kept its answers in `data/cache/`, which is git-ignored, is not the content
  volume, and is not in the state snapshot. Cloud Run scales to zero, so every
  cold start re-requested every word the learner looked at — and spaced
  repetition guarantees the same words come back. The module whose one loud
  rule is "single lookups only, they ask not to be batched" had storage that
  made it re-ask forever. Same shape as the circuit breaker's module-level
  dict, and worse, because the state existed to protect a third party.
- **"Don't rebuild what exists" needs re-testing once the thing exists.** It
  was right about paradigms and flashcards and wrong about meaning. The app
  knew 160 316 words and could not say what one of them meant, so a B1
  object-case drill on `etendus` or `rahakott` trained morphology on a token
  the learner could not translate. A plan decision made before anything was
  wired is a hypothesis; check it against what the app actually lacks.
- **Read the whole response before deciding which field is the good one.**
  `sonapi` returns translations twice. The obvious top-level key is English
  only; the per-meaning key carries Russian, which is the language this app
  explains everything in. Reading the obvious one threw away the field that
  mattered most, and the card looked complete while doing it.
- **`--help` proves the parser, never the body.** `cli.py` is the largest
  module here and had 0 % coverage — nothing had ever imported it, while six
  routes were deleted, four generators were unified and `Cloze` was rebuilt
  underneath it. Nothing was broken, which is only knowable by running it:
  every read-only command now runs in the suite with stdin at EOF, so the next
  refactor that renames something out from under a command fails here instead
  of the first time the operator types it. 0 % → 54 %.
- **A fixture that hand-rolls a schema is a second schema.** `conftest`
  wrote its own `CREATE TABLE items` for the content database. It had drifted
  twice over: no `sources` table at all, and no `added_on NOT NULL`. So the
  fixture looked complete while `library.sections` — and therefore
  `/api/library`, `/api/status` and two CLI commands — could never run against
  it. Build fixtures with the app's own opener and writer, and a test that
  passes is testing the shape production has.
- **Verify "it works in CI" in a clean worktree, not in your build.** The
  suite was green locally and red in CI for the ordinary reason: `data/` is
  git-ignored, so the developer has a corpus and CI does not. `git worktree
  add` gives exactly CI's tree in one command — cheaper than a round trip
  through Actions, and it found both remaining failures.
- **A synthesiser answers the question you ask, not the one you meant.**
  Vabamorf refuses to decline a verb, which quietly implied it would refuse for
  anything with no paradigm. It does not: asked for the genitive of the adverb
  `alguses` it returns `algusese`, of `dna` it returns `dnad`, of the
  imperative `õpi` a full declension. 319 of 7 256 exported paradigms were
  invented that way and `/api/lookup` printed them in the same citation format
  as `raamat, raamatu, raamatut`. Gate on part of speech before asking —
  `wordlist.declines`.
- **Two callers of one linguistic fact will not stay in step by themselves.**
  `morph.case_forms` round-trips every candidate and refuses when several
  survive; its docstring names `kool` (which naively yields the *cola*
  paradigm) and `reis` (the thigh, not the journey) as why. `export.py` did
  `next(iter(synthesize(...)))` — the exact naive version that function
  replaced — and shipped `kool, koola, koola` to the word card. The drill path
  was right and the card path was wrong for as long as both existed.
- **A class-scoped fixture outruns the function-scoped redirect.** pytest
  builds higher-scoped fixtures first, so a `scope="class"` fixture calling
  `connect()` with no argument reads the *real* `config.DB_PATH` — the autouse
  redirect in `conftest` has not run yet. On a machine with a built word list
  it quietly used 160 316 real lemmas and passed; on CI it created an empty
  `data/eesti.db`, exported nothing, and left the phantom file behind to fail
  two unrelated tests later in the run. One mistake, five failures, three of
  them in files it never touched. Pass the path explicitly.
- **A key that looks set and is not costs more than a missing one.** A `.env`
  line reading `export OPENROUTER_API_KEY=sk-...` — what you get from copying
  any shell instruction — set a variable literally named
  `"export OPENROUTER_API_KEY"`, which nothing can read back, and `load()`
  reported it as loaded. Same failure as the `explains` grep: the check said
  healthy while production was offline. Strip `export `, validate the name,
  and never announce a key you did not set.
- **A derived cache must not outlive the thing it derives from.**
  `wordlist.build` replaced `words` and left `object_cases` — its own Vabamorf
  cache, keyed on those very words — untouched, while `index_object_cases`
  skips anything already cached. So the cache was write-once for the life of
  the database: a refresh could neither drop a paradigm for a word upstream
  had removed nor recompute one whose part of speech had been corrected. The
  docstring said "idempotent — safe to re-run after a refresh", and that was
  true of the table it named and false of everything downstream. Rebuilding
  costs 2.4 s.
- **A connection bound at import cannot be redirected either.** The rule was
  already written for *paths*; a connection is worse, because it captures the
  path and keeps it. `app.py` calls `_bind_breaker()` at module scope, so the
  circuit breaker held an open handle to the real `data/progress.db` from the
  first moment anything imported the app — and every `breaker.reset()` in the
  suite wrote to the learner's own study record. Reading a developer's data
  makes a test lie; writing to it loses their work.
- **"Every database" meant three of seven.** `conftest` redirected the word
  list, the corpus and the form index, and left progress, review, vocabulary
  and the correction queue pointing at `data/`. The docstring said "every".
  Count them.
- **A comment recording a fixed bug is not a test.** `parse_episode` carried
  three of them — entities never decoded, `.m3u8` audio rejected so two whole
  archives looked empty, and a transcript required so the audio-only series was
  discarded — with nothing to stop any of the three coming back. The harvesters
  are excluded from the suite because they talk to third parties, and that is
  right for `fetch`; their *parsers* are pure functions over a string and are
  where every bug these modules have had actually lived. Test those with
  synthetic markup: real ERR and Selges keeles text is owner-only and must not
  be committed, and only the shape is being parsed anyway.
- **Coverage finds what review does not.** Reading the least-covered modules
  found a module with no importer at all, three cleaning defects, and a
  documented rule with no enforcement. None of them were visible from the
  features that use them.
- **Count the orphans, do not fix them one at a time.** After the sixth
  page/API drift bug, measuring showed **10 of 47 routes had no caller at
  all** — 21 % of the surface. The worst was `POST /api/vocab/known`, the only
  way a word can be marked known: its other caller is the CLI, which does not
  exist on the deployment, so on the running app no word could ever become
  known and every feature ordered by known vocabulary sat at zero for good.
  `tests/test_route_inventory.py` now fails on a route nothing can reach.
- **An endpoint with no caller is the same bug as a measurement with no
  writer.** `/api/modes` returned every section with its counts and its
  Russian note, and nothing called it — while the page hardcoded the one
  section it knew about.
- **Measure before generating a distractor.** The obvious word-order drill —
  swap two constituents, offer the swap as wrong — was abandoned after
  measuring 1 000 native sentences: 75.4 % follow the rule, not ~100 %, and
  the exceptions were mostly the classifier failing to tell a fronted
  adverbial from an adverb modifying the subject. That is syntax, and this
  project has morphology. A distractor that is sometimes correct Estonian
  teaches the opposite of the rule.
- **Attested beats inferred.** Where a learner wrote it and a native fixed it,
  correctness is given and needs no analysis to defend. It is why the
  word-order items are 47 real corrections rather than thousands of generated
  ones.
- **Do not state a rule harder than the handbook does.** EKK says the finite
  verb is *usually* second and calls inversion a means of emphasis. An
  explanation saying "always" would have the learner correcting good Estonian.
- **A queue with no drain is not a feature.** Corrections could be queued for
  the error log from the app and sent only by a CLI that does not exist on the
  deployment. The queue filled forever, and the verdict counted queued rows as
  though they were in the log.
- **A store is not a feature until the screen has a shape for it.** The gloss
  layer landed and the screen got the leftovers: one 12px grey line reading
  `protsent, osastav — процент · A2` — the word to operate on, the form to
  produce, what the word means and its CEFR level, four roles joined by three
  separators at one weight, with the new information the least visible thing
  on the card. Give each role its own treatment, and colour by **role, not by
  language**: the rule explanation is Russian too, so painting all Russian
  alike would have made the rule and the meaning identical.
- **When a fix needs a method the mixin already has, the copy is the bug.**
  `Cloze` said "same surface as `drills.Drill`" and meant it literally: it
  predated `item.GradedItem` and carried its own `check`, `solution`,
  `reference` and `to_dict`. That went unnoticed for months because everything
  worked — until the page needed `label` and cloze items came back with no
  case in the instruction row. Adding `label` alone would have left five
  copies where there should be none. Measure the copies against the original
  before deleting them (425 real items: identical grading, identical
  references, no reachable difference), then delete them.
- **A database key on screen is a bug even when it renders.** `overview.py`
  had already fixed this once for the path panel — `kusisonad` is not a thing a
  learner recognises — and the review queue was still printing `obj-case`
  beside every card. Resolve ids where the API answers, not in each page that
  happens to show one.
- **Open the app in a browser at the size it will be used.** The phone was
  checked for months; one look at 1440px found a layout that used a fifth of
  the screen and three panels that could not be opened at all. Both sizes,
  every tab.
- **A bounding box is not visibility.** A layout assertion that filters on
  `getBoundingClientRect().height > 0` reports six phantom "controls trapped
  under the navigation" on the phone, because Chromium gives descendants of a
  collapsed `<details>` a real rect while they are unrendered and unhittable.
  `checkVisibility()` is the question being asked; `elementFromPoint` at the
  element's own centre is the one that matters for "can a thumb reach this".
  The first UAT pass produced four suspected mobile defects and three of them
  were the measurement, not the app.
- **A filter that silently shows one slice is worse than one that errors.**
  `kõik` on the reading list sends no band filter, which is correct, and then
  `ORDER BY added_on DESC LIMIT 60` returns 60 rows of whichever band was
  harvested last — so the option that means "everything" showed a third of the
  corpus and looked identical to `kergem`. A limit applied after an ordering
  that correlates with the thing being browsed is a filter bug wearing a
  pagination costume. Third time this shape has cost real content: 82
  unreachable items, the `level`/`band` rename, now this.
- **Reproduce the ordering before trusting the reproduction.** The first
  fixture for that bug inserted three bands and passed for the wrong reason —
  `add_items` stamps every batch inside the same second, so "newest" was
  arbitrary, and the guard test written alongside it is what caught that. Two
  numbers have to mirror reality for the defect to appear at all: the limit
  must be smaller than one band, as 60 is smaller than 116.
- **Look at the screen, not only at its geometry.** A full UAT pass with
  assertions on visibility, overflow and hit-testing found five defects and
  cleared three false alarms. Then reading the *screenshots* found four more in
  minutes, none of which any assertion could have caught: database keys in the
  path labels (`astmevaheldus ← gen-stem`), the same sentence three times in
  one drill, a raw JS TypeError shown to the learner, and a silent button. A
  measurement answers the question you thought to ask; a picture answers the
  ones you did not.
- **When reviewing a selection step, look at the set and not at the items.**
  Two unrelated-looking bugs were one shape: the reading filter let recency
  fill the whole limit with a single band, and the drill generator let uniform
  sampling cluster ten items onto five frames. Every individual row was valid
  and correct in both cases, which is exactly why every existing test passed.
  Ask what the *collection* looks like — how many distinct bands, how many
  distinct sentences — because that is the property the learner experiences.
- **A tab that is not in the URL is a tab the browser cannot help with.**
  Refresh lost the learner's place, `#status` did nothing, and Back left the
  app — one missing mechanism, three symptoms. The first fix used
  `replaceState` to avoid a history stack and kept the worst symptom: Back
  still left. In a tabbed interface Back means "the tab before", and on a phone
  Back is a system gesture rather than a button somebody chose. `pushState` per
  change, `replaceState` for the landing tab, and re-selecting the current tab
  pushes nothing.
- **Re-tapping the thing you are already on should do nothing.** Clicking the
  active mode reset it to its first tab, which was a mild annoyance for months
  and became a real bug the moment the tab lived in history: it pushed an entry
  the learner never chose, so Back landed somewhere they had never been.
