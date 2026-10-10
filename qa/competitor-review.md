# Competitor review: Sõnarada

Input for S11 (`qa/opus-sessions.md`), the discussion with the owner about how
Klint's exercises and screens should differ from the generic pattern it shares
with others. Written on 10 October 2026 from the owner's material. It is
analysis and opinion, not a decision: nothing here changes `DESIGN.md` or
`PRODUCT.md`.

## Material

Nineteen screenshots, a seven-minute desktop walkthrough recorded by the
author on a development build, her post asking for ideas, and replies under
it. They are third-party images, so they stay outside git, in the main
checkout's research/competitors/sonarada folder, with an index of the
recording by second. The voice-over was not transcribed; everything below
comes from the picture. No phone layout, prices or native app were seen, and
the correctness of the content was not assessed.

## What it is

A teacher's own platform for her courses, in Russian, for Russian speakers
learning Estonian: group online lessons, and self-paced "marathons" at A1, A2
and B1 (B1 is being moved over). The dictionary and the grammar trainer come
with a course's price. Five top-level areas: *Марафоны*, *Словарь*,
*Грамматика*, *Заметки*, *Профиль*. The author says she built it with AI tools.

## The product, area by area

| Area | Sõnarada | Klint today |
|---|---|---|
| Home | Course cards with generated or stock images and a progress count; "what else is on the platform". | Täna: one next task. |
| Course | Continue, lessons with progress ("7 из 50"), the teacher's name, a marathon leaderboard. | Kursus: thirty units with checks and a mastery gate; milestones without points, streaks or ranks. |
| Lesson | One long page per lesson; its parts (*osa*) in a side column; numbered tasks, each with its own check and "ask the teacher": a YouTube video, matching sentence halves, a paragraph whose gaps are drop-downs with a glossary under it, new words, words dragged under pictures (one left over), listening gaps, a 20–100-word text in a rich-text editor. | The session: learn → practise → check, one item at a time. Unit dialogues and texts exist but are on no unit page yet. |
| A word in a text | Select it: forms, senses, add to the dictionary, or open Sõnaveeb in a separate browser window. | Tap it: the word card with the reading Vabamorf picks in that sentence, EKI's example phrases with Russian, *Kordamisse*; the learner stays in the app. |
| Dictionary | "My words": principal forms, Russian, audio (Sõnaveeb's recording where the teacher has none); status set by hand (learn, review, learned) with bulk actions; add any word, choosing its meaning; a side panel in every lesson. | Sõnavara: five-word practice and a collection by level and part of speech; a status on the word card; review by FSRS. |
| Word trainer | *Заучивание*: a new word passes several task types (meet it with a picture the learner may pick, pairs, picture, letters, by ear, principal forms); a miss sends it back. *Повторение*: spaced review. The learner picks the source (dictionary, course, lesson), batch size and task types. | Sõnatrenn (typed recall against the word list); FSRS review, vocabulary self-rated; an EVS phrase rebuilt from tiles. |
| Grammar | Tests by topic, grouped by grammar area and level, 10/20/30 sentences from a pool of about a thousand; last and overall percentage per topic; a cheat-sheet image per topic. Item: a sentence with a drawn blank and four forms in a 2×2 grid; translation and glosses behind spoilers; after a miss both forms coloured, "your answer", "right answer" and the cheat sheet. | Drills for 42 topics graded by code from Vabamorf and the item's key; a Reegel page per topic; *Selgita* (Haiku, labelled) after a miss; only the first attempt counts; grammar items in FSRS. |
| Notes | Notes linked to course → lesson → part → task through long native selects; a notes page grouped by lesson; a chip leads back to the task. | None. |
| People | "Ask the teacher" from any task; group classes; a leaderboard. | No teacher; a model helper, labelled; no ranks by design. |
| Exam and speaking | Not seen in this material. | HARNO's shape, mocks in its task types, official tasks, sitting and countdown, readiness per part; read-aloud, the exam question bank, *Vestlus*, speech recognition. |

## What it does well

1. **A visible collection loop.** A lesson's words go to "my words" in one
   click, any word in any text can be added, and the trainer drills what was
   collected. The learner watches a dictionary of their own grow.
2. **Acquisition before spacing.** A new word is met several times, in
   different ways, before it enters review; a picture can carry its meaning.
3. **Support on request.** Translation and glosses sit behind a tap, so the
   item is tried first.
4. **The rule at the moment of a miss**, one tap away.
5. **Notes on the exact task**, a habit adult learners bring from paper
   courses.
6. **An honest test setup**: which topics, which level, how many sentences,
   how many exist.
7. **A person behind it**: her video, her voice, a group, someone to ask. This
   is the strongest asset, and it is not a design one.

## Where it is weak

**Look.**
- The default look of an AI-built web app: grey page, white rounded cards,
  one teal accent, small sans text, outline icons, every element at the same
  weight. An AI-style cartoon portrait on the main course stands in for an
  identity.
- Desktop density: small text, many controls per screen, wide empty margins,
  buttons floating over content. No phone layout was seen.
- Five kinds of surface for related things — page, side panel, modal,
  popover, and a separate browser window for Sõnaveeb, which takes the
  learner out of the app.

**Flow.**
- A lesson is a scroll of a dozen cards, each with its own check and its own
  "ask the teacher". There is no single next action, and no sense of progress
  inside a part beyond the side list.
- Results are colour fills and counts ("Верно 2 из 7"); what to do next is
  left to the learner.

**Learning.**
- Recognition, not production. Drop-downs, a 2×2 choice, matching and
  dragging all show the answer among the options; with four close forms,
  elimination often finds it. The exam's writing and speaking ask the learner
  to produce the form.
- A miss costs little. Matching ends "when every pair is green", so trying
  pairs finishes it; per-topic percentages come from a handful of answers.
- Feedback says what, not why: the right form and a cheat sheet, but not which
  case, why this sentence wants it, or what the learner's form would have
  meant.
- "Learned" is a button the learner presses; only words are spaced, grammar
  has scores but no memory.
- A leaderboard rewards volume.

## What Klint shares with it

The owner's point, and it holds: the same audience, levels and building
blocks — a sentence with a drawn blank, a choice or a typed form, a dictionary
of forms with Russian, a word trainer, grammar topics with a rule page,
model-made material, an AI-assisted build. Side by side, a learner would see
one kind of product. Even the name converged: an assistant once offered the
owner the same name, Sõnarada. That is the lesson. Whatever
an assistant proposes first — the blank with options, cards on grey, a teal
accent, a stock hero — is what the competitor already has. Defaults converge.

## Where Klint is already ahead, and hides it

- **Correct by construction:** forms from Vabamorf and EKI, graded by code,
  sources named on the page.
- **Memory:** grammar items as well as words in FSRS; the first attempt
  counts; a mastery gate.
- **Production:** typed answers, dictation, read-aloud, *Vestlus*, writing
  checked for object case, rection and agreement.
- **The exam:** HARNO's own shape and task types, official tasks, the sitting,
  readiness per part.
- **Context:** the reading Vabamorf picks in this sentence, EKI's example
  phrases with Russian, EKI's readers' voices.
- **Free.**

None of this shows on a first screen. Her features are things a learner can
point at — my 68 words, my notes, my 53 % — while Klint reads as a set of
tools, and her product as a course with a teacher.

## Opinion: how Klint could be clearly better

Directions for the S11 discussion, not decisions.

1. **Start from the learning problem, not an exercise catalogue.** For
   `obj-case` the problem is "is the action complete?", not "genitive or
   partitive?". An exercise built on that question will not look like
   anyone's gap-fill.
2. **Produce, don't pick — and lose the drawn blank.** Concepts worth a
   prototype, each still graded by code with the first attempt counting:
   - the word stands in the sentence in its dictionary form and the learner
     reshapes it in place; the interlinear word then names what it became;
   - two sentences that differ only in the form (*sõin leiba* / *sõin
     leiva*): which one says the bread is finished? The form carries meaning,
     which is what the topic is about;
   - find the wrong form in a sentence, then fix it;
   - say it: answer aloud, and Vabamorf checks the form in the transcript;
   - build it from parts, stem and ending, with the stem changing;
   - from a situation (a picture, a Russian intention) to an Estonian phrase.
3. **One thing at a time, one primary action.** Klint's session already
   works this way; a lesson should not become a page of twelve checks.
4. **Feedback that teaches in a line.** After the attempt: the form named
   under the word, one sentence of why from EKK in Russian, and what the
   learner's form would mean if it is a real form; *Selgita* for more. A
   shape and a word as well as colour.
5. **A collection that is earned and visible.** A word joins "my words" when
   it is met in a text or missed in a drill, its state comes from review
   rather than a button, and the learner sees what they can now produce —
   words and forms — rather than percentages of three questions.
6. **Notes on the thing itself.** A line of the learner's own on a rule, a
   word or an item, shown again wherever that thing returns, instead of a
   separate tree of lessons.
7. **Help without pretending to be a teacher.** "Ask about this", grounded in
   the item and labelled as a model; for a learner who has a teacher, a way
   to share the question or the mistake list.
8. **Phone first, with an identity from Estonian rather than stock art.** The
   Interlinear tokens (S10) give the typography and colour; the exercise
   should feel like reading Estonian, not like filling a form.
9. **Show the depth early.** The sitting, readiness per part, words and forms
   gained: the first screens can show what Klint knows about the learner that
   a course page cannot.

**Not worth copying:** the leaderboard, a "learned" button, drop-down gaps,
the 2×2 grid of forms, lookups in another window, colour formatting in
writing, generated imagery.
**Worth adopting in Klint's own form:** several encounters before review,
meaning on a tap, "add every word of this text", notes, and the rule at the
miss.

## Questions for the owner

- Which concepts above should be prototyped first, and on which topic
  (`obj-case` is the natural first)?
- Are notes wanted, and on what: rules, words, items?
- Pictures for words: wanted, and from where, given the licence of each
  image?
- Should Klint serve learners who also have a teacher (share a question,
  export mistakes)?
- How much visible count, given no points, streaks or ranks?
- Which apps of 2026, in any field, does the owner admire? A list before the
  session would steer the survey.
