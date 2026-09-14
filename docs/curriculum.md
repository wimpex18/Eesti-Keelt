# Curriculum

The A1→B1 grammar syllabus as data, and the learning model around it.

## Where it lives

`eesti/curriculum.py` — `TOPICS`, 36 topics taken from Estonian course
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
- **Placement and test-out** use the same mastery check: harder items until the
  learner fails (`placement.py`); any available topic can be tested out.
- **Checkpoints** are mixed end-of-level quizzes (`checkpoint.py`).
- **Themes** pair a grammar rule with a themed word set (`themes.py`), so a
  drill teaches the rule and the vocabulary together.
- **Reference topics** (no generator) show in the path and never block.

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
| comparison, numerals, question words | closed-class tables |
| word order | attested learner corrections (EstGEC-L2), not generated swaps |
| rection | EKK SÜ 64's list of attested confusions |
| punctuation | comma before a subordinate clause |

An item ships only when its answer is unambiguous; a distractor that is
sometimes correct Estonian is never generated.

## Not doing

- Hand-written lesson prose — EKK is the reference, linked per topic
  (`grammar.py`).
- Half-life regression — FSRS-6 is in use.
- A fixed linear course, gamification or streaks.
