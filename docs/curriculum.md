# Curriculum

The A1→B1 grammar syllabus as data, and the learning model around it.

## Where it lives

`eesti/curriculum.py` — `TOPICS`, 41 topics taken from Estonian course
curricula that track the state standard (Keeltekeskus Kaja A1/B1, Dialoog,
B-Lingua). Each `Topic` has `id`, `level`, Estonian and Russian names,
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
  tested out from `Kogu rada`; the sweep over the whole syllabus is CLI-only.
- **Checkpoints** are mixed end-of-level quizzes (`checkpoint.py`).
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
| object case, locative cases, principal forms | Vabamorf synthesis, round-trip validated; nouns whose genitive = partitive are excluded |
| verb forms, conjugation | Vabamorf; drilled where the naive form differs from the real one |
| cloze | real harvested sentences, only where the case is named or forced (negation) |
| comparison, numerals, question words | closed-class tables; a question word's Russian cue is EKI EVS's (below) |
| word order | attested learner corrections (EstGEC-L2), not generated swaps |
| rection | EKK SÜ 64's list of attested confusions |
| punctuation | comma before a subordinate clause |

An item ships only when its answer is unambiguous; a distractor that is
sometimes correct Estonian is never generated.

**Question-word cues.** A `kusisonad` item shows, beside `küsisõna`, the
Russian for the word its blank wants (`____ sa elad?` → где), so the learner
knows what to ask without seeing the Estonian. The Russian is EVS's
(`eesti/evs.py`, `question_senses`), chosen by rule: the one EVS article with
an adverb or pronoun headword equal to the answer; in it, the first sense EVS
illustrates with a direct question opening with the word; that sense's first
group, neutral translations only. No such article, two of them, or a cue the
distractor shares — no cue. 8 of 12 answer words have one; `kelle`,
`kellele`, `kellega` (forms of `kes`, not headwords) and `kui palju` (two
words) have none. Grading does not read the cue.

## Not doing

- Hand-written lesson prose — EKK is the reference, linked per topic
  (`grammar.py`).
- Half-life regression — FSRS-6 is in use.
- A fixed linear course, gamification or streaks.
