# Roadmap — what to build next, and why

> **Version 1.0 closed on 2026-08-20.** For the honest inventory — what works,
> what was never built, what is knowingly broken, and what the research plan
> promised and did not deliver — see **[status.md](status.md)**. This file is
> the reasoning behind the choices; that one is the state they left things in.

Informed by what the 2026 language apps do well, what their users complain about,
and what this project can do that they structurally cannot.

## What the market gets right

| App | The idea worth stealing |
|---|---|
| **Migaku** | Turns real content (Netflix, YouTube, web) into cards with one click. FSRS scheduling. No manual deck building. |
| **LingQ** | Tracks known vs unknown words *as you read*, so the library adapts to you. |
| **Anki** | FSRS-6, and the fact that nobody has beaten plain scheduling on retention. |
| **Readlang** | Click-to-translate in the reader; friction near zero. |

Two findings recur across current reviews:

1. **People leave streak apps when the streak stops improving the skill they
   care about.** Gamification retains; it does not teach. Whatever gets built
   here should be measured against "did my error log shrink", not "did I
   practise today".
2. **Spaced repetition plus content you actually met beats scripted lessons.**
   The reason given is context: a word met in a real sentence reloads the scene
   on recall. Cards built from a curriculum have no scene to reload.

## The grammar half of the market

The four above are vocabulary tools, which is most of the market and not most of
this project's problem. The apps that actually teach *structure* work differently
and are worth separating out.

| App | The idea worth stealing |
|---|---|
| **Babbel** | Grammar is introduced **inside a dialogue**, then drilled — never as a standalone rules page. CEFR-aligned A1→B2 with an explicit syllabus you can see. |
| **Busuu** | Per-skill CEFR tracking A1→C1, and an explicit **placement test** so you enter where you are rather than at lesson 1. |
| **Clozemaster** | Cloze deletion over **sentences from a real corpus**, not authored examples. Grammar practice as a side effect of context. |
| **British Council** | Each grammar point ships with a short reference, then graded practice at two difficulties. The reference and the exercise are the same unit. |

Three of these change something concrete here:

1. **Cloze from the corpus, not from templates.** Every drill in this app comes
   from a template I wrote, which caps variety at my imagination and produced
   sentences like *"Ma ostsin haigla ära"* until semantic pools were added. There
   are **349 harvested Selges keeles texts** on disk, in real Estonian, already
   lemmatised and case-labelled by Vabamorf. Blanking the object in an authentic
   sentence gives a drill whose answer is *known correct because a native wrote
   it* — and no pool of plausible objects to maintain. Template drills stay for
   the contrasts the corpus does not happen to contain.
2. **Placement before lesson 1**, not as an afterthought. Already step 4 of the
   curriculum plan; Busuu's version is the argument for it not slipping.
3. **The reference and the exercise are one unit.** Done: every cloze item
   carries its EKK section, so the rule is on the same screen as the exercise
   rather than a page away. Items whose topic has no tagged rule report *no*
   reference rather than a nearby-looking one.

Babbel's dialogue framing is the one deliberately skipped: it needs authored
conversations, which is exactly the hand-written lesson prose `curriculum-plan.md`
rules out.

## What this project can do that they cannot

Every one of those apps builds a **vocabulary** card, because a general-purpose
tool cannot know *why* a word was hard.

This one can. Vabamorf knows `raamatut` is the partitive of `raamat`; the Notion
error log knows partitive-for-genitive is the documented weakness. So a word met
while reading becomes a **grammar** card for the pattern behind it — the drill
that would have prevented the mistake — not a translation to memorise.

That is the differentiator, and it is only available because the morphology is
deterministic and the error history already exists.

## Built

- **Review scheduler** (`eesti/review.py`) — FSRS-6 via `py-fsrs` (MIT), rather
  than a hand-rolled interval scheme. Models difficulty, stability and
  retrievability per item; needs 20–30 % fewer reviews than SM-2 for the same
  retention. Re-adding an item keeps its schedule, so meeting a word again does
  not wipe the memory model built for it.
- **The loop is closed** (`eesti/mining.py`). A drill answered wrong enqueues
  itself *already marked missed*, so FSRS schedules it soon rather than treating
  it as fresh. Clicking a word in the reader queues the **grammar pattern**
  behind it with the sentence as context — LingQ's move, but producing an
  object-case card rather than a translation.

  Words with nothing to teach are **refused with a reason**: `kino` has an
  identical genitive and partitive, so there is no contrast to drill, and a card
  that cannot be got wrong wastes the scarcest resource in spaced repetition.
- **Known-word tracking** (`eesti/vocab.py`) — Lute's 1-5 status model, but held
  **per lemma** rather than per surface form, because `raamat` and `raamatut`
  are not two things to learn. The library orders by what is comprehensible now
  instead of by a static difficulty band.
- **Corpus cloze** (`eesti/cloze.py`) — Clozemaster's idea against the 349
  harvested texts: 1 138 case items and 28 negation items whose answers are
  correct because a native wrote them, with no semantic pool to maintain. The
  hard part was refusing the unsound ones — see `curriculum-plan.md` for the
  two routes by which an authentic sentence gets a unique answer.
- **Learner-corpus weighting** (`eesti/harvest/evkk.py`) — 51 467 annotated
  errors ranking the nine tags by what learners of Estonian actually get wrong,
  as a counterweight to a single error log.
- **Dictation** (`eesti/dictation.py`) — the Kuulamine tab had no exercise. It
  was a text-to-speech box: paste a passage, hear it read. Nothing could be
  answered, so nothing was scored and nothing recorded, and the verdict went on
  reporting listening as untouched however much had been played — on an exam
  where a zero in one part fails you regardless of the other three.

  A sentence from the corpus is spoken at 0.7×, the learner writes down what
  they heard, and the submission is aligned against the transcript word by
  word. The answer is correct because a native wrote it, grading needs no
  model, and — unlike the read-aloud loop, which compares against what a
  *recogniser* heard — a miss here is a real miss, so the result carries no
  caveat about the model's Estonian.

  Missed words are deliberately **not** queued for review: a word missed in
  dictation may be evidence about hearing rather than about grammar, and an
  object-case card raised from a mis-heard word teaches the wrong lesson from
  the right mistake.
- **Word order** (`eesti/wordorder.py`) — the second-largest error class in the
  learner corpus (11.4 % of all EVKK marks, 19.3 % of those the nine tags
  cover) and, until now, the largest tag with **no drill at all**. `sonajark`
  was a topic the path could reach and never practise.

  The items are **attested, never generated**, and that was a measurement
  rather than a preference. The obvious generator — take a sentence, swap two
  constituents, offer the swap as wrong — would teach V2. Measured against
  1 000 native-corrected sentences restricted to single-clause declaratives
  opening with a fronted element: **75.4 % invert, 24.6 % do not**, and almost
  all of the non-inverting quarter turn out to be `Just ühiskond on…`,
  `Peaaegu kõik mehed tahavad…` — a leading adverb modifying the *subject*
  rather than a fronted constituent. Telling those apart is syntax; this
  project has morphology. It is the same boundary Vabamorf already has with
  object case.

  So items come from pairs where a learner wrote it and a native corrected it,
  filtered to corrections that only re-order. Correctness is given rather than
  inferred, and nothing is claimed about the learner's version being
  ungrammatical — the question asked is which one a native wrote, which is how
  the exam is marked. The explanation says "обычно вторым", matching EKK
  (SÜ 90) and the 75.4 %, because an absolute rule would have the learner
  "correcting" good Estonian.
- **The listening shelf, which had been unreachable.** Two of the seven library
  sections — the harvested listening archive (54 items) and the 28
  radio-course transcripts, 13 % of everything harvested — were indexed,
  sectioned and covered by API tests, and could not be opened from the app.
  The page could only ask the library by *skill*, and only ever asked for
  `lugemine`. It cost more than hidden content: the readiness verdict measures
  Kuulamine by library items opened, so that half of the evidence could never
  move.

  The list is now rendered from `/api/modes` — which returned exactly this and
  had no caller — so adding a section to `SECTIONS` surfaces it without anyone
  remembering the page.
- Reading library (349 texts), object-case and verb-form drills, writing check,
  TTS, ERR episode audio, rection and inflection type via `sonapi`.
- **Word card enrichment, finished.** `sonapi` returned two translation sets and
  the module read the wrong one: the top level carries English only, while each
  meaning carries `rus`/`eng`/`fra` weighted. An app whose language policy is
  Russian was showing a muuttüüp number to someone who did not yet know the
  word. Per-meaning is read first now, top-level fills gaps, and the card ends
  with a link out to Sõnaveeb for the paradigm and audio this app deliberately
  does not rebuild. The speaking panel links EKI's pronunciation exercises and
  the A1–B1 phrase collections for the same reason — "use it, don't build it"
  is only a decision once the learner can reach it.
- **A meaning layer, which the app had never had.** 160 316 words, a CEFR level
  and a full paradigm for each, and no way to say what any of them meant — so a
  B1 object-case drill on `etendus`, `luuletus` or `rahakott` was morphology
  practice on a token. `eesti/gloss.py` stores each Sõnaveeb answer in
  `vocab.db`, which the snapshot carries, and the meaning now shows on the word
  card, in the hint of a practice item, on the verdict after answering, and in
  the review queue. It also fixes a worse bug in the other direction: the old
  cache lived on the container's disk, so Cloud Run emptied it on every cold
  start and the app re-requested the same words forever. Asked once, ever, and
  capped per day — a stricter reading of "do not batch them" than before.
- **And a screen shaped for it.** The instruction under a drill was one grey
  run-on carrying four different things; it is now a row where the word, the
  form to produce, the meaning and the level each read as what they are. The
  meaning has its own colour token — by role rather than by language, because
  the rule explanation is Russian as well and must stay distinct from it. The
  review queue stopped printing curriculum ids at the learner, the word card
  puts the meaning with the word instead of under the buttons, and the count
  of glossed words appears under Sõnavara, which is where `gloss.stats` got
  the reader it had been written without.

## Deployed, and verified against the running app

Live at a `workers.dev` URL behind Cloudflare Access: a Cloudflare Worker in
front of the FastAPI app on Google Cloud Run, both on free tiers. See
`deploy.md` for why it is split that way and what each half refuses to do.

Checked by request against production, not by reading the code — which is how
three of these were found at all:

| | |
|---|---|
| the app, end to end | 160 316 words indexed, drills generated by Vabamorf at request time |
| grading | server-side; a wrong answer is rejected by the server, not the browser |
| speech | TTS → Whisper → alignment, 4/4 words, caveat attached |
| the origin | 403 to anything that is not the Worker |
| the front door | 302 to an Access login for anyone who is not the owner |

## Next, in order

0. ~~**Redeploy.**~~ **Done 2026-08-20.** PR #17 merged at 12:21 and Cloud
   Build had the new image serving by 12:24 — confirmed by the `built` stamp on
   `/api/health`, not assumed from a green workflow. The invented paradigms are
   gone from the running app.

   It also surfaced the thing now at the top of this list: the deep smoke check
   found the **grammar checker in offline mode on the deployment**
   (`llm:openrouter: HTTPError` — the key is present and the call fails).
   Writing still flags candidates and typos, but no correction carries an
   explanation, so nothing reaches the Notion log. PR #18 makes the note name
   the status code, which is what decides between waiting and replacing a key.
1. **Use the readiness verdict.** It is built and it says "ei ole veel" for
   both levels, with the reasons named. As of 2026-08-20 those reasons for A2
   are: no exam part touched at all, 0 of 7 A2 topics mastered, and the
   checkpoint unattempted. There is **no countdown any more** — the 2026
   sitting was declined, the exam is planned for 2027, and no date is chosen.
   The next work is not more features. It is study, and then watching those
   three numbers move, because they are what decides A2-then-B1 against
   B1-alone.
2. **Whatever the verdict names.** It reports untouched exam parts first,
   because ≥60 % overall with one part at zero is still a fail. That list is
   the honest backlog.
3. **The topics with no generator**, if a build is wanted rather than a study
   month. Counted and listed in `status.md` — deliberately not repeated here,
   because the number moves (13 → 11 on 2026-08-21) and two files claiming it
   is two files that can disagree.

### The upload happened — this is no longer blocked

`content.db` is on the deployment. The smoke run of 2026-08-19T22:48Z reports
`reading library ......... OK`, which is `"library":true` from `/api/health`,
so the three things that rode on it are live: the 349-text reading library,
dictation's sentence pool, and the 47 attested word-order items.

Re-run `bash deploy/push-content.sh data/content.db` from Cloud Shell only
after a *new* harvest. Nothing in the current branch needs it — see below.

### Tags with no drill, and whether that is a gap

| Tag | State |
|---|---|
| `word-order` | **built** — attested items, see above |
| `vocab` | no drill, and none intended: it is the largest class (24.2 %) but it is word *choice*, which the reading library, the known-word tracking and the review queue already work on. A grammar drill is the wrong shape for it. |
| `gradation` | no drill of its own. `astmevaheldus` is reference material and the contrast it teaches is already drilled through `gen-stem`, which is where the stem is actually chosen. 0.8 % of corpus marks — the smallest of the nine. |

## The official material, and what is deliberately not done with it

Both official sources are indexed: **EIS** (23 interactive self-scoring tasks)
and **harno.ee** (39 task PDFs and listening tracks, 17 A2 and 17 B1, every
exam part covered). The readiness verdict counts them per part, so "practise
listening" reads as "13 official B1 listening tasks, here they are".

All of it is **pointers**. `body` is empty and a test holds it there. Studying
from HARNO's files is ordinary personal use; copying a hundred of a state
agency's exam files into a database on a public deployment is not, and neither
is using them as training data for a model. Linking gives the learner
everything a copy would, and holds none of it.

## Known gaps, stated plainly

- **The deployment is running an image from before the current branch.** The
  last smoke run checked image `2026-08-19T22:02:22Z` against commit `25814b3`,
  which predates the export fixes. Until it is rebuilt, the word card there
  still prints `kool, koola, koola` and the other 319 invented paradigms. The
  fix rides the image — `RUN python -m eesti.cli export` at build time — so a
  redeploy is all it needs, with no content push.
- **A crash between snapshots loses a few minutes of answers.** The alternative
  is moving learner state to D1, which is a real rewrite of the storage layer
  and is not worth it for that.
- **`rektsioon` is dark if EKI refuses the build machine.** Deliberate: the
  fetch is non-fatal, so one topic degrades rather than the whole image failing.

## Deliberately not doing

- **Streaks, XP, leagues.** The thing every review says stops working.
- **Chrome extension / Netflix integration.** Migaku does it well and it is a
  large surface; the ERR and Selges keeles corpora are enough material.
- **Our own scheduler.** FSRS is trained on ~700M reviews. Rolling one would be
  strictly worse.
- **Speaking practice as a solo loop.** The B1 exam's speaking task is *paired*;
  a monologue recorder trains the wrong thing (see `speaking.md`).
