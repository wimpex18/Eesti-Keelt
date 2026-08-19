# Roadmap — what to build next, and why

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
- Reading library (349 texts), object-case and verb-form drills, writing check,
  TTS, ERR episode audio, rection and inflection type via `sonapi`.

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

1. **A2 rehearsal readiness.** The optional sitting is 07.11.2026, decided by
   01.10.2026. The app is level-parameterised already; what is missing is an
   honest A2 checkpoint that says yes or no.

The **official exam tasks are indexed** (`eesti/harvest/eis.py`): 23 published
practice tasks, of which 7 A2 and 7 B1, split between reading and listening.
Two corrections to the plan came out of probing rather than reading: `aine=R`
(*Eesti keel teise keelena*) returns **nothing at all**, and `keeletase` is the
filter that works; and the catalogue is 23 tasks, not an open-ended archive.

They are stored as **pointers, never copies**. The task body lives in an iframe
on HARNO's site, it is their copyright, and the scoring and immediate feedback
that make a task worth doing only work there — so a scraped copy would be dead
text *and* a redistribution risk, while a link buys everything.

The Notion write-back landed (`eesti/notion.py`): confirmed errors queue
locally and go to the existing `Vead` log only when `cli notion --push` is run,
after showing what would be sent. The nine tags are pinned against the live
database, because the log's "three of a tag is this week's focus" rule is what
made `obj-case` the priority in the first place — an invented tag would never
group, never reach three, and never become anyone's focus.

## Known gaps, stated plainly

- **The reading library is empty in production** until a harvest is pushed.
  The mechanism exists (`deploy/push-content.sh`); the harvest has not been run
  and uploaded.
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
  a monologue recorder trains the wrong thing (see `sources.md`).
