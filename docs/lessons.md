# Habits this codebase has earned the hard way

Every entry here is a bug that reached the learner, or a check that reported
healthy while it had not. They were written one at a time in `CLAUDE.md` until
that file was 48 KB and a fresh session read it before doing anything; they
live here now, unchanged, grouped so a session can read the two or three
groups its work touches.

**Read the group that matches what you are about to change.** If you are
adding a state, read *Measurements with no writer*. If you are touching the
page, read *The page*. If you are about to trust a check that says OK, read
*Providers, secrets and operating the deployment*.

These are records, not live claims: several of them quote a number that was
wrong, which is the whole point of the entry. `tests/test_docs_match_code.py`
therefore does not check this file, for the same reason it does not check
`CLAUDE.md`.

## Paths, connections and state that must survive a restart

A value bound at import cannot be pointed anywhere else, and Cloud Run
scales to zero — so anything held in a module global is gone by the next
study session. Seven entries, one shape.

- **Resolve paths at call time, not at import.** A module-level constant cannot
  be pointed anywhere else, and three bugs in a row came from that.

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

- **Two names for one file is a fork waiting to happen.** `app.py` kept its own
  copies of the four learner database paths, bound at import from `config`.
  The entry in `status.md` called that "correct today, the same shape as the
  breaker binding" — and it was already worse than that: `_state_paths()` and
  the database helpers both read the copies, so redirecting one name without
  the other pointed a restore at a file the app never opened. It failed only in
  tests, silently, by writing somewhere real. When a value has two homes, the
  question is not whether they agree now but what happens the first time one
  moves.

- **Fixing a latent pattern surfaces who depended on it.** Consolidating those
  paths onto `config` broke twelve test redirects that patched `app` alone.
  That is not a reason to leave the pattern; it is the measurement of how far
  it had spread. The fix is to pair them and pin the invariant with a test that
  redirects `config` and demands both the snapshot and the helpers follow.

## Measurements with no writer, endpoints with no caller

The costume changes every sprint; the tell never does. Nothing fails,
because the other branch keeps working, so the feature looks finished.

- **A measurement without its writer measures nothing.** Three times now: the
  vocabulary table nothing ever wrote to, the snapshot restore that always
  refused, and `/api/library/{id}` reading without recording. When you add a
  reader, find the writer; when you add a writer, check something calls it.

- **Presence of a database is not presence of data.** Two separate bugs came
  from checking that a file existed: the first request creates it *with its
  schema*, so an empty deployment looked full. Count rows.

- **Check the contract in both directions.** `test_ui_contract.py` had asked
  "does every endpoint the page calls exist?" since it was written, and never
  "can every section the API serves be reached?". 82 items — 13 % of the
  library — were indexed, sectioned, API-tested and unopenable. A one-way
  contract test finds typos; it does not find things nobody wired up.

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

- **A queue with no drain is not a feature.** Corrections could be queued for
  the error log from the app and sent only by a CLI that does not exist on the
  deployment. The queue filled forever, and the verdict counted queued rows as
  though they were in the log.

- **A value nothing can set is a value that does not exist.** The vocabulary
  ladder had five statuses and three of them — `tuttav`, `eiran`,
  `teadsin ammu` — had no writer anywhere: modelled, stored, counted by the
  overview, unreachable from any control. This is the third costume of the
  same bug (a measurement with no writer, an endpoint with no caller), and the
  tell is identical: nothing fails, because the two statuses that *are* set
  keep every downstream feature looking correct. When you add a state, find
  the thing that sets it; when you find a state nobody sets, decide whether to
  wire it or drop it, and write down which.

- **The schema had already declared the missing feature.** `review_items.kind`
  has read `-- curriculum topic id, or 'vocab'` since the file was written, and
  nothing had ever inserted a `vocab` row. That is the third costume of the same
  bug — after the measurement with no writer, the endpoint with no caller, and
  `[data-theme]` with no control — and the most useful, because a declared-but-
  unwritten value is a note from a past session saying *this is the shape of the
  thing that is missing*. Grep the schemas for values nothing produces.

- **A value nothing can produce is the bug this repo keeps having.** Four in
  four sprints, each in a different disguise: a measurement with no writer, an
  endpoint with no caller, `[data-theme]` read by the stylesheet and set by
  nothing, `kind="vocab"` declared in a schema and never inserted, and now
  `FAMILIAR` — a rung on the vocabulary ladder with no writer, no stored rows,
  and one reader that ORed it with a value that *is* written. None of them
  broke anything, which is the whole difficulty: the other branch keeps
  working, so the feature looks finished. The general check is cheap and now
  exists for the ladder — assert every named value round-trips through a named
  writer. Worth doing for any enumeration before adding to it.

## Derived, never hand-maintained

A list of things that already exist somewhere drifts from them silently,
and so does a second copy of one job.

- **Never hand-maintain a list of things that already exist somewhere.**
  `TABS` was a literal list of the panel names and it drifted from the panels
  themselves: three of ten were missing, so one panel never hid and two never
  showed. Nothing failed — every click still produced *a* panel. Derive the
  list from the thing it describes, and if it cannot be derived, test that the
  two sides correspond in **both** directions.

- **The same job written twice becomes two behaviours.** Four harvesters each
  had a private `_TAG_RE`; on one line of input they gave three answers, and
  every difference reached the learner — undecoded entities in 27 000 words of
  transcript, two words joined into one, and a space before every full stop
  that the punctuation drill then showed as correct. The copies were the bug,
  not any of the three symptoms.

- **When a fix needs a method the mixin already has, the copy is the bug.**
  `Cloze` said "same surface as `drills.Drill`" and meant it literally: it
  predated `item.GradedItem` and carried its own `check`, `solution`,
  `reference` and `to_dict`. That went unnoticed for months because everything
  worked — until the page needed `label` and cloze items came back with no
  case in the instruction row. Adding `label` alone would have left five
  copies where there should be none. Measure the copies against the original
  before deleting them (425 real items: identical grading, identical
  references, no reachable difference), then delete them.

- **A hand-written map of states drifts from the code that emits them, and it
  drifts silently.** `progress.TopicProgress.state` returns five strings. The
  page's `RU` map glossed `reference`, `ready` and `locked` — the three an
  account with *no progress* displays — and carried `done` and `review`, which
  nothing has ever emitted. So `mastered` and `in progress` reached the screen
  as raw English: a learner who finished a topic was shown the word `mastered`
  as their reward. The earlier fix for "the path badges are English" looked at
  a screen and glossed what was on it, which is why the two states that only
  appear *after* you do something were the two it missed.

## Tests and fixtures

A green suite is a claim about the code, and these are the ways that claim
has been false.

- **In-process is a blind spot, and it hid a bug for three commits.** An
  empty `data/eesti.db` kept appearing and nothing could be shown to make it.
  Eight CLI commands were creating it — `wordlist.connect()` makes the file and
  applies the schema, so *reading* the lexicon manufactured one — and
  `test_cli_smoke` runs every one of those commands and could never catch it,
  because it calls `cli.main()` in-process where the autouse fixture redirects
  the path. The spy could not see it either: a monkeypatched `sqlite3.connect`
  does not cross an interpreter boundary. What worked was `sys.addaudithook`
  in a `sitecustomize.py` on `PYTHONPATH` — inherited by every subprocess —
  and, faster still, running the eight commands by hand instead of the suite.
  When a suite that exercises the culprit stays green, suspect the harness, not
  the absence of a bug.

- **Reproduce with the real argument form.** `cli readiness A2` looked clean in
  the manual hunt and `cli readiness --level A2` created the file: argparse
  rejected the first before any code ran, and "no phantom" was recorded as
  evidence of innocence. The regression test derives its command list from
  `test_cli_smoke.READ_ONLY` rather than restating it, which caught five
  creators the hand-written hunt had missed.

- **Test the property, not the source text, when the same call can be right or
  wrong.** The first guard here grepped `eesti/cli/` for `wordlist.connect` and
  flagged four files — including `cli build` and `cli export`, which open the
  word list to *write* it and must keep creating. A grep cannot tell a reader
  from a builder. Running every read-only command against an unbuilt path and
  asserting no file appears can, and it is the behaviour that actually matters.

- **A guard that asks `exists()` is defeated by the thing it guards against.**
  `cli serve` refuses to start without a database, and an empty word list
  satisfied `exists()` — so it served the whole app with a zero-word lexicon:
  every drill empty, every lookup missing, no message anywhere. The browser
  fixture had the same gate, where a phantom would have unskipped ~140
  journeys against an empty lexicon. Count rows. It is the same rule as
  "presence of a database is not presence of data", and it has now cost three
  separate guards.

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

- **A class-scoped fixture outruns the function-scoped redirect.** pytest
  builds higher-scoped fixtures first, so a `scope="class"` fixture calling
  `connect()` with no argument reads the *real* `config.DB_PATH` — the autouse
  redirect in `conftest` has not run yet. On a machine with a built word list
  it quietly used 160 316 real lemmas and passed; on CI it created an empty
  `data/eesti.db`, exported nothing, and left the phantom file behind to fail
  two unrelated tests later in the run. One mistake, five failures, three of
  them in files it never touched. Pass the path explicitly.

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

- **A scheduler tested without time passing measures nothing.** Grading one
  FSRS card five times in the same second showed the interval frozen at two
  days, which reads exactly like a broken spaced-repetition system — and is
  the algorithm working: FSRS deliberately gives almost no stability gain for
  a card reviewed long before it is due. Reviewed *at* the due date the same
  card expands 10 min → 2 d → 11 d → 47 d → 171 d → 514 d. The defect report
  was already written when the second test was run. Anything scheduled in time
  has to be tested by advancing time, not by repeating the call.

- **Reproduce the ordering before trusting the reproduction.** The first
  fixture for that bug inserted three bands and passed for the wrong reason —
  `add_items` stamps every batch inside the same second, so "newest" was
  arbitrary, and the guard test written alongside it is what caught that. Two
  numbers have to mirror reality for the defect to appear at all: the limit
  must be smaller than one band, as 60 is smaller than 116.

- **The test that prevents a bug can have the bug's own shape in it.**
  `test_ui_language` catches an Estonian grammar term written in Cyrillic —
  written after `omastav` shipped as **омастав** in nine places. Fixing a
  *different* finding, `омастав` was typed straight back into
  `mining.py`, and the check said nothing: its list of modules to scan was a
  hand-written tuple of seven filenames and `mining.py` was not on it. A
  guard against a hand-maintained list, implemented as a hand-maintained
  list. Deriving it — any module with Cyrillic in it is prose — found a real
  one hiding behind the old list on the first run: `speaking.py` told the
  learner *"это прошедшее время, лихтминевик"*. Two refinements it then
  needed, both about what the learner can actually read: a **comment**
  explaining the bug and the `REPAIRS` search-and-replace table both have to
  contain the misspelling, so the scan reads string literals via `ast` and
  subtracts the repair table.

- **A source scan matches prose, and prose about a function is not a call to
  it.** Four times in one sprint. Three were assertions I wrote that passed on
  their own explanatory comment — searching a workflow step's `run:` for a
  construct the comment above it also names, twice, and a Worker check for
  `startsWith("/api/state/")` that its own "this used to be" comment satisfied.
  The fourth was an *existing* test: `grep -rln set_status eesti/` counted a
  docstring in `readiness.py` that explained a measurement had been taken
  "through `vocab.set_status`", and reported a fourth writer of the vocabulary
  ladder. A check that cannot tell a mention from a use fails on documentation,
  which teaches people to stop writing it. Strip comments before searching, or
  better, **parse**: `ast` distinguishes a `Name`, an `Attribute` and a
  `FunctionDef` from a word in a sentence, and the definition site is a
  different thing again from a caller.

## The page: layout, CSS, the browser, and what the learner reads

Most of these were invisible to every assertion in the suite and obvious in
a browser at the size the app is actually used.

- **A store is not a feature until the screen has a shape for it.** The gloss
  layer landed and the screen got the leftovers: one 12px grey line reading
  `protsent, osastav — процент · A2` — the word to operate on, the form to
  produce, what the word means and its CEFR level, four roles joined by three
  separators at one weight, with the new information the least visible thing
  on the card. Give each role its own treatment, and colour by **role, not by
  language**: the rule explanation is Russian too, so painting all Russian
  alike would have made the rule and the meaning identical.

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

- **Look at the screen, not only at its geometry.** A full UAT pass with
  assertions on visibility, overflow and hit-testing found five defects and
  cleared three false alarms. Then reading the *screenshots* found four more in
  minutes, none of which any assertion could have caught: database keys in the
  path labels (`astmevaheldus ← gen-stem`), the same sentence three times in
  one drill, a raw JS TypeError shown to the learner, and a silent button. A
  measurement answers the question you thought to ask; a picture answers the
  ones you did not.

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

- **Install the engine your learner actually uses.** WebKit was a documented
  gap for months on the grounds that it "would need a download". One
  `playwright install webkit` later, the first run found the worst defect of
  the whole QA pass: landing on an exam-mode link threw
  `Cannot access 'examLevel' before initialization`. Both engines had it —
  Chromium raised it as an *unhandled rejection* nobody had subscribed to,
  WebKit as a page error where it could be seen. The panel rendered anyway, so
  every visibility assertion passed in both. A second engine is not redundancy;
  it is a second reporter, and they do not report the same things.

- **Listen for unhandled rejections, not only for errors.** Every loader here
  is `async`, so a throw inside one never reaches `window.onerror`. A test
  harness that subscribes only to `pageerror` is deaf to the entire async half
  of the application, which is most of it.

- **Bootstrap last.** The line that opens the first panel belongs at the end of
  the script, not in the middle where the routing happens to be written.
  Opening a panel runs its loader, and a loader may touch anything declared
  anywhere in the file; from the middle, everything below is in the temporal
  dead zone. Moving the one variable that broke would have fixed one instance
  and left the trap set for the next loader.

- **A fix can be the next bug's cause.** Hash routing was the fix for "refresh
  loses your place"; it created the dead-zone crash by making the exam loader
  reachable at load time, and it turned a months-old annoyance — re-tapping the
  active mode resets its tab — into a history entry the learner never chose.
  Re-run the whole pass after a fix, not just the test that failed.

- **`textContent =` on a decorated element deletes the decoration.** Every
  async button here does the same dance: `btn.textContent = "Проверяю…"` while
  the request is in flight, then `btn.textContent = "Kontrolli"` to restore.
  That assignment replaces *every* child — and once the buttons carried a
  Russian gloss, the gloss was one of those children. So the first click on
  `Kontrolli` or `Harjuta`, the two most-used controls in the app, permanently
  removed the only word on them the learner can read, and it stayed gone until
  a reload. Nothing failed; the button still worked; the label was still
  correct Estonian. It is the same shape as a measurement with no writer — an
  addition that the code already there quietly undoes — and it is invisible to
  any test that renders the page without clicking anything. `setLabel` writes
  the text and puts the span back.

- **A `var()` with no definition is a declaration that does nothing, silently.**
  Two of them had been in the stylesheet for as long as anyone had looked:
  `.vocword{color:var(--fg)}` — the token is `--ink` — and
  `.topic.mastered .st{color:var(--ok)}`, where `--ok` has never existed. The
  second is the worse one, because the selector *does* match: `mastered` is a
  real state, so the single row in the path list that represents finished work
  was coloured by a rule that resolved to nothing. Neither is visible in review
  (`var(--ok)` reads as correct until you go looking for the definition) and
  neither is visible in a screenshot, because the element is present and sized
  and simply takes the inherited colour. `tests/test_design_tokens.py` asks the
  sheet whether every token it reads is a token it writes.

- **A reset copied to where it does not apply deletes what it was protecting.**
  Thirteen elements carried an inline `margin-top:0`, all saying the same
  thing: "I am the first child of this panel and its padding is already the
  space above me." Four of the thirteen were **not** first children, and there
  the idiom silently changed meaning from "remove the margin I do not need" to
  "remove the margin I do need" — the Harjuta row jammed against the progress
  ring, the pass rule against the level buttons, the review row against its
  hint, a listening hint against its heading. The reported symptom was one of
  the four. The fix is one `.panel > :first-child{margin-top:0}`, which cannot
  be copied onto something that is not first, and the other three came back on
  their own. Spacing lives on a scale now (`--s1`…`--s6`), because eleven
  hand-chosen margins is how a page gets to the point where "a bit more room
  here" means inventing a twelfth.

- **A grid whose children are placed by row number breaks when you add a
  child.** `.wrap` is a two-column grid on the desktop and `.rail` is pinned
  at `grid-row:3 / span 40`, which silently assumes header, nav, panels in
  that order. Adding one `<span>` at the top level — a group marker beside the
  tab bar — made it a grid item, pushed every row down, and opened a 500px
  void between the header and the tabs. Nothing about the span was wrong; the
  coupling was. Anything added at the top level of `.wrap` has to be placed
  deliberately, and a marker belongs inside the thing it marks anyway.

- **`display:flex` on a parent changes what `display:block` means in a child.**
  Giving `.modes button` `display:inline-flex` to seat an icon turned its
  `.ru` gloss — a block that had been stacking *under* the Estonian label —
  into a flex item sitting *beside* it. The control went from 330px to 534px
  and pushed a 390px phone 164px sideways. The nav tabs were untouched by the
  same change because their gloss lives inside `.lbl` rather than directly on
  the button. Before making a container flex, look at what its children were
  relying on the normal flow to do.

- **A refusal is a sentence the learner reads, and it must be true of the
  word in front of them.** `from_reading`'s refusal said "omastav ja osastav
  on samad" for every word it turned down — including adverbs and
  conjunctions, which have neither form. It also told the learner to "open
  the word card", where the only button that could act on the advice had just
  disabled itself and was never re-enabled. Refusal paths get the same
  scrutiny as success paths: they are more likely to be read closely, because
  something has just not worked.

## Content, third parties and the language itself

What a rule is allowed to claim, whose server it costs, and which slice of
the material a selection step actually returns.

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

- **A filter that silently shows one slice is worse than one that errors.**
  `kõik` on the reading list sends no band filter, which is correct, and then
  `ORDER BY added_on DESC LIMIT 60` returns 60 rows of whichever band was
  harvested last — so the option that means "everything" showed a third of the
  corpus and looked identical to `kergem`. A limit applied after an ordering
  that correlates with the thing being browsed is a filter bug wearing a
  pagination costume. Third time this shape has cost real content: 82
  unreachable items, the `level`/`band` rename, now this.

- **When reviewing a selection step, look at the set and not at the items.**
  Two unrelated-looking bugs were one shape: the reading filter let recency
  fill the whole limit with a single band, and the drill generator let uniform
  sampling cluster ten items onto five frames. Every individual row was valid
  and correct in both cases, which is exactly why every existing test passed.
  Ask what the *collection* looks like — how many distinct bands, how many
  distinct sentences — because that is the property the learner experiences.

- **A decision that was right about its own case gets applied to everything.**
  `mining.from_reading` queues the object-case contrast behind a word met while
  reading, and refuses words that have no contrast — a card that cannot be got
  wrong wastes review time, which is the scarcest thing in spaced repetition.
  Correct, and it was being applied to a third of the vocabulary it does not
  describe: **31.3 % of A1–B1 words have identical genitive and partitive**
  (791 of 2 531; A1 35.8 %, A2 34.9 %, B1 28.5 %). All of them were refused
  with "pole midagi harjutada" — telling the learner there was nothing to
  practise about a word they had just clicked *because they did not know it*.
  The refusal message even said "omastav ja osastav on samad" when the real
  reason was often "we do not know what this word means yet". The module
  docstring argued the case honestly and only for the words it had in mind;
  nothing checked how many words it was actually deciding for. Measure the
  share of inputs a rule refuses before trusting the rule.

- **Keeping the schedule is not the same as freezing the card.**
  `review.add` returns early on an existing id so that meeting a word again
  does not reset the memory model — correct, and it kept the *text* too. A
  meaning card built from a one-word seed gloss stayed one word for ever,
  even after Sõnaveeb supplied richer senses, and re-mining still reported
  "lisatud kordamisse" as though something had happened. The schedule is a
  fact about the learner and must survive; the prompt and answer are
  renderings of what the app currently knows and should be refreshed.
  `context` is neither — it is the sentence the word was first met in, which
  a later encounter does not improve, so it is only filled if empty.

## Providers, secrets and operating the deployment

Every one of these reported healthy while production was not.

- **A third party being down must never fail the build.** EKI, HuggingFace and
  EIS are all optional at build and test time, loudly.

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

- **A key that looks set and is not costs more than a missing one.** A `.env`
  line reading `export OPENROUTER_API_KEY=sk-...` — what you get from copying
  any shell instruction — set a variable literally named
  `"export OPENROUTER_API_KEY"`, which nothing can read back, and `load()`
  reported it as loaded. Same failure as the `explains` grep: the check said
  healthy while production was offline. Strip `export `, validate the name,
  and never announce a key you did not set.

- **A retry can be the thing that keeps the failure alive.** The deployment
  sat at `HTTPError 429` for three days and the reading was "free tier spent,
  it will clear". OpenRouter counts *failed* attempts against the daily quota,
  and this client retried a 429 three times — so every rate-limited check
  spent three of the fifty confirming it was rate-limited, and cost the learner
  fifteen seconds doing it. Two different limits wear that one status code and
  only the per-minute one is worth waiting out. Before adding a retry, ask what
  the failed attempt costs and whether the server has told you which failure it
  was; `Retry-After` is that answer.

- **A cheap check that reports on configuration must not be worded like a
  check on behaviour.** `grammar explains ........ OK` printed in the same
  smoke run where the deep check reported `vabamorf-offline` and
  `llm:openrouter: HTTPError 429`. `/api/engines` reads configuration and says
  so in its own docstring — a provider whose free tier is spent still answers
  `can_explain: true`. The earlier fix here was grep-versus-jq, which was a
  real and different bug; this one is the wording. Two checks in one run
  contradicting each other has already cost a debugging round chasing a Cloud
  Run traffic split that did not exist. Name what was verified: "configured
  (live call unproven)".

- **A check that fires on event A, about a system that changes on event B, is
  green about the wrong thing — and the timing makes it look right.** `smoke`
  fires when `deploy` completes. `deploy` deploys the Worker; the app is a
  container built by a Cloud Build trigger on `main`. So the smoke run that
  fires on a merge reports on the *previous* image, every time, and it does it
  within a minute of the merge, which is exactly when a reader is looking and
  most inclined to believe it. Measured: merge 20:11:20Z, smoke green at
  20:12:11Z about an image built 14:39:50Z, the real image landing 20:14:20Z —
  and the merge in question was the one carrying a Python runtime change whose
  only open risk was whether the image builds. The run already printed both
  facts and never compared them. When a check cannot observe the thing it is
  named after, make it **say which version it looked at** rather than
  suppressing or failing it: a warning that names the staleness costs nothing
  on the runs where the timing is fine, and a failure on every merge is a check
  people learn to scroll past. Same family as "a measurement with no writer"
  and the service worker's hand-edited cache version: the wiring looked
  connected and was not.

  **And if event A is filtered more narrowly than event B, the check does not
  fire at all.** Found three commits later, in the same workflow. `deploy` is
  filtered to Worker paths; Cloud Build rebuilds on every push to `main`; so
  every merge touching only `eesti/`, `tests/` or `docs/` redeployed the app
  with no check running — `deploy` had 8 runs against roughly 17 merges. The
  first half of this lesson makes a check honest about *what* it looked at; it
  says nothing about whether it ran. Ask both: does this fire on every change to
  the thing it checks, and does it look at the version that change produced?

- **"No answer" and "a blank answer" are different, and collapsing them
  fabricates data.** `_ask_terminal` caught `EOFError` and `KeyboardInterrupt`
  and returned `""`. `""` grades as wrong, so `cli placement </dev/null` wrote
  fifteen wrong attempts to the learner's record, Ctrl-C could not leave a
  sweep the command advertised as interruptible, and `cli checkpoint` also
  wrote a failed checkpoint and queued every un-shown item for review — all
  feeding the readiness verdict. When a value means "the person is not there",
  give it its own type and let it stop the loop; **raise rather than return a
  sentinel**, because a caller that forgets to check a `None` grades it, which
  is the original bug wearing a new hat. And when two outcomes must stay
  distinct, do not reuse a return value that already means something else — an
  abandoned checkpoint returning the same empty result as "no items could be
  built" is two states with one representation.

- **A list called `READ_ONLY` is a promise, and the test that walks it must run
  the real thing.** `test_cli_smoke` ran every command on that list and asserted
  a clean exit — in-process, where the autouse fixture redirects the databases
  the promise is about. So the one property the name asserts was the one thing
  never checked, for as long as the list existed. Ask a safety property of a
  **subprocess**, compare the artefacts **byte for byte** rather than counting
  rows, and derive the cases from the list itself. This is the second bug found
  this way, after the phantom word list, and both hid in the same gap between
  "the suite exercises this command" and "the suite exercises this command the
  way a person runs it".

## Documents and decisions

A document is a measurement, and it goes stale the same way any other one
does — silently, while still reading as true.

- **A true sentence goes stale silently.** The speaking screen promised the
  recording never left the device. That was true; then recognition moved to
  Cloudflare and the sentence stayed, sitting under a second notice that said
  the opposite. Claims about privacy, cost and provenance are facts about the
  code — pin them with a test that fails when the code changes.

- **A document is a measurement, and measurements need writers too.** Every
  count in `docs/` was taken by hand, once. Four were wrong on the same day —
  13 topics without a generator when there were 11, 42 API routes when there
  were 49, 1 141 tests when there were 1 283, 21 of 36 topics with practice
  when it was 25 — and every one had been true when written. Worse, one
  document drew a *structure* the app never had (a top-level `Raamatukogu`,
  `Kordamine` nested inside `Õppimine`, no speaking or writing tab) and a later
  session planned against it as if it were a map. `tests/test_docs_match_code.py`
  now derives each of those claims from the code and fails naming the file and
  line, because the same rule that applies to a stale cache applies to a stale
  sentence. A doc may still record a past figure — it just has to say "at the
  time of writing", which the check honours.

- **Not every documented bug is a bug.** `sonapi`'s file cache was on the list
  for evaporating on cold starts. Following the callers showed every runtime
  path goes through the durable gloss store, and the only user of the file
  cache is `cli rections` — which runs inside the Docker build, where a cache
  that lives for one build is exactly right. It was downgraded with the reason
  written down, rather than moved to make a list shorter. A fix nobody needs is
  still a change that can break something.

- **The section that says what is missing goes stale fastest, and it is the one
  that steers the next session.** `docs/status.md`'s "What a learner still
  cannot do" listed three gaps; all three were built within a day and the
  section stayed as written for a further sprint. A fresh session reading it
  would have rebuilt `Sõnavara` — reasonably, and for nothing. Delete an entry
  the moment it ships, and check the section against the code before trusting
  it, the same way a claim about privacy or provenance gets pinned with a test.
