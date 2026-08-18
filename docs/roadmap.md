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
- Reading library (349 texts), object-case and verb-form drills, writing check,
  TTS, ERR episode audio.

## Next, in order

1. **Known-word tracking.** The reader already computes coverage per text; record
   which words have actually been met, and order the library by what is
   comprehensible *now* rather than by a static difficulty band.
4. **Notion write-back** to the existing `Vead` database, so confirmed errors
   join the hand-curated log rather than living in a parallel one.
5. **Cloudflare deploy** — Workers + D1 + Pages behind Access. Access is not
   optional: it is what keeps the owner-only material (HARNO, ERR) private on a
   public URL.

## Deliberately not doing

- **Streaks, XP, leagues.** The thing every review says stops working.
- **Chrome extension / Netflix integration.** Migaku does it well and it is a
  large surface; the ERR and Selges keeles corpora are enough material.
- **Our own scheduler.** FSRS is trained on ~700M reviews. Rolling one would be
  strictly worse.
- **Speaking practice as a solo loop.** The B1 exam's speaking task is *paired*;
  a monologue recorder trains the wrong thing (see `sources.md`).
