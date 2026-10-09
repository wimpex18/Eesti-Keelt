# Curriculum

The syllabus as data, from the first sounds to B1, and the learning model around
it. The course arranges these topics into thirty one-week units
(`docs/course-structure.md`, `eesti/units.py`); this file is the topic layer.

## Where it lives

`eesti/curriculum.py` — `TOPICS`, 46 topics: the grammar taken from Estonian
course curricula that track the state standard (Keeltekeskus Kaja A1/B1,
Dialoog, B-Lingua), and the first week's sounds, phrases and numbers. Each `Topic` has `id`, `level`, Estonian and Russian names,
`requires` (prerequisites), an optional error-log `tag` and an optional
`generator`. `curriculum.validate()` rejects cycles and unknown prerequisites;
`order()` derives the study path. Which topics have no generator is in
`docs/status.md`.

Error tags (`config.TAGS`) must match the Notion `Vead` multi-select options
exactly: `obj-case`, `loc-case`, `gen-stem`, `gradation`, `verb-form`,
`ma-da-inf`, `word-order`, `vocab`, `rektsioon`.

## Learning model

- **Prerequisites are real.** Every case except nominative and partitive is
  built on the genitive stem, so `gen-stem` precedes the cases, plurals and
  comparison; the path is derived from the graph, not hand-ordered.
- **Mastery, not completion.** A topic is mastered at 8 correct of the last 10
  attempts over at least 5 distinct items (`progress.py`).
- **Blocked, then interleaved.** A new topic is drilled on its own until
  mastery, then its items join the FSRS review pool (`handoff.py`), which mixes
  everything due.
- **Placement and test-out** use the same mastery check: topics are probed in
  path order, five of five each (`placement.py`). Any available topic can be
  tested out from Kursus; the sweep over the whole syllabus is CLI-only. The
  first week (unit 1) is not probed: the assessment starts at A1.
- **Checkpoints** are mixed end-of-level quizzes (`checkpoint.py`); the A1
  checkpoint leaves out the first week.
- **Course order** is the units': the next topic is the first available one in
  unit order, and the units follow the graph (a test holds them to it). The
  first week leads only until the learner has mastered something beyond it.
- **Themes** pair a grammar rule with a themed word set (`themes.py`), so a
  drill teaches the rule and the vocabulary together.
- **Reference topics** (no generator) show in the path and never block.
- **Every topic has a Reegel page** (`eesti/lessons.py`, `/api/lesson/{topic}`). Its prose restates EKK or the EKI teatmik and names the section; its tables are synthesised by Vabamorf for a few sample words, except the pronoun table, which is the EKI teatmik's *Asesõnade käänamine* (`eesti/pronouns.py`), because Vabamorf declines pronouns wrongly. Each table carries a `source` note that the page shows.
- **Every topic has a representation** (`curriculum.representations`): a
  generator, an EKK reference, linked reading, practice inside another topic's
  drills (`CROSS`), or the checkpoint. Topics with none are listed with the
  reason in `REPRESENTATION_GAPS`, and a test holds the two together.
- **Weak rules and refresh** (`learner.py`), from the evidence:
  - accuracy is recency-weighted, with a 14-day half-life;
  - a rule is weak below 70 % over at least 6 answers, or when its cards are
    remembered below 80 %;
  - a mastered topic whose cards fade, or that has been untouched for 60 days,
    comes back as a refresh. Mastery itself is never revoked.
- **Today's plan** (`planning.py`, Rada's "Plaan") fills a time budget in this
  order:
  1. due reviews (at most 40 %);
  2. the weakest rule, showing the last mistake in it again;
  3. a refresh;
  4. the exam part practised least this week;
  5. the next topic;
  6. a text within reach.

  It is a pure function of the evidence, so the same day and evidence give the
  same plan. Every block says why it is there, in Russian.

## Picking material for a beginner

Reading texts and read-aloud sentences are chosen by one measure,
`difficulty.within_reach`: the share of **running words** (Vabamorf lemmas,
punctuation dropped) that are *within reach* — marked known by the learner, or
at **A1–A2** on the word list (EKI's official level where the list has one).
The level belongs to each word; a text is ranked by the share and never given a
CEFR level.

| | Lugemine *soovitatud sulle* (`/api/reading/next`) | Rääkimine *Loe ette* (`/api/speaking/readaloud?kind=lause`) |
|---|---|---|
| Counted | every word except names, numerals, abbreviations | every word, names and numbers included (`strict`) |
| Cut-off | at least **80 %** within reach (`FLOOR`) | **3–8 words**, all within reach |
| Order | by coverage in 5-point steps, shorter first inside a step | qualifying sentences shuffled by seed |
| Too few | none clears 80 %: the least hard, flagged `fallback`, with a Russian warning | filled with the most within reach, shorter first |

The numbers come from the reading-coverage literature: readers need about
95–98 % of running words known for unassisted reading (Hu & Nation 2000;
Laufer & Ravenhorst-Kalovski 2010), and at 80 % none of Hu & Nation's readers
comprehended adequately. 80 % is therefore the cap on what is recommended, and
the bands `iseseisev` (≥ 95 %), `arendav` (≥ 90 %) and `raske` say how far each
text is from unassisted reading. The list note says in Russian how it was
chosen.

## Priorities

Two sources weight what to practise:

1. the learner's own error log (Notion `Vead`) — first weight;
2. EVKK, the learner corpus (`harvest/evkk.py`): among the nine tags, word
   order and rection are the largest annotated error classes after vocabulary;
   object case is small in the corpus but is this learner's #1 weakness.

## Generators and what they guarantee

| Generator | Source of truth |
|---|---|
| object case, locative cases, principal forms | Vabamorf synthesis, round-trip validated; nouns whose genitive = partitive are excluded. The nominative total object (imperative, impersonal, *da*-infinitive, plural) uses `morph.unique_form` for nominative and plural forms, and is drawn only by rule name (`drills.BASE_RULES`) |
| partitive subject (`osaalus`) | EKK SÜ 35: a negated subject is partitive; a plural partial subject leaves the verb singular, so the verb's number keys the case. Vabamorf forms; no affirmative substance is asked, since either case is right there |
| sounds (`tahestik`) | EKI's PSV recordings and their marks: II against III quantity in one spelling, one vowel letter, short against long (`eesti/sounds.py`) |
| phrases (`fraasid`) | EKI's *Kasulikke väljendeid A1*, keyed by its grouping and two-part exchanges; the pairs of functions whose phrases serve each other (`phrases.APART`) never share a choice (`eesti/phrases.py`) |
| numbers (`arvud`) | a table of number words written as EKK O 42 writes them, each a numeral to Vabamorf (`eesti/numbers.py`) |
| verb forms, conjugation | Vabamorf; drilled where the naive form differs from the real one |
| conjugation and imperative in phrases | EKI EVS's example phrases, credited: a verb is blanked only where Vabamorf reads it one way out of context, never an `o` form in a phrase with *ei* (the connegative reads the same) (`conjugation.phrase_drills`) |
| negation beyond present and past | the forms EKK M 99 names — *ei elaks*, *ärge elage*, *ei elata*, *ei ole ~ pole elanud* — under the topic whose form each is (`tingiv`, `kaskiv`, `umbisikuline`, `taisminevik`); EVS phrases where the negation stands right before the gap, frames otherwise; no negated conditional with a first- or second-person subject (`eesti/negation.py`) |
| modal + infinitive (`ma-da-inf`) | which infinitive *võima*, *saama*, *tohtima* (da) and *pidama* (ma) take, read off EVS's phrases — idioms (*hakkama saama*), infinitive chains and *saab olema* left out, a modal shown with both dropped (`eesti/modals.py`) |
| future (`tulevik`) | EKK SÜ 27: the present after a future adverbial EVS translates as such (*homme* «завтра»), against the past; *hakkama* in the present + ma, against da. The *saama*-future (SÜ 28) is never graded, and a phrase holding *saama* + a ma-infinitive is not used (`eesti/future.py`) |
| cloze | real harvested sentences, only where the case is named or forced (negation); outside the owner's scope, EKI EVS's example phrases whose target word the word list puts at the learner's levels (`evs.phrases`) |
| comparison, numerals, question words | closed-class tables; a question word's Russian cue is EKI EVS's (below) |
| word order | attested learner corrections (EstGEC-L2), not generated swaps; outside the owner's scope, EKI EVS noun phrases rebuilt from tiles, only those whose order EKK fixes: genitive and agreeing attributes before the head, none of SÜ 104's free orders (`wordorder.phrase_tiles`) |
| rection | EKK SÜ 65's list of attested confusions |
| punctuation | comma before a subordinate clause, in corpus sentences or EKI EVS's phrases |

An item ships only when its answer is unambiguous; a distractor that is
sometimes correct Estonian is never generated.

**Question-word cues.** A `kusisonad` item shows, beside `küsisõna`, the
Russian for the word its blank wants (`____ sa elad?` → где), so the learner
knows what to ask without seeing the Estonian. The Russian is EVS's
(`eesti/evs.py`, `question_senses`), chosen by rule: the one EVS article with
an adverb or pronoun headword equal to the answer; in it, the first sense EVS
illustrates with a direct question opening with the word; that sense's first
group, neutral translations only. A word with no article — `kellele`,
`kellega` (forms of `kes`) and `kui palju` (two words) — is read off EVS's own
questions that open with it (the next word not an adposition): the opening of
one or two words that more than half of their Russian renderings share
(«кому», «с кем», «сколько»). Two articles, no majority, or a cue the
distractor shares — no cue. 11 of 12 answer words have one; `kelle` has none,
because EVS renders it seven ways (чью, чей / чья / чьё, чья, чьим, кто…).
Grading does not read the cue.

## Not doing

- Hand-written lesson prose — EKK is the reference, linked per topic
  (`grammar.py`).
- Half-life regression — FSRS-6 is in use.
- A fixed linear course: units order the path, and any topic can still be
  opened, tested out or skipped.
- Gamification or streaks.
