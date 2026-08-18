# Grammar curriculum: research, gap analysis, and plan

The goal: everything a traditional A1→B1 textbook teaches, with the ability to
skip what is already known, quizzes that check it, progress that persists, and
grammar learned alongside vocabulary rather than separately.

---

## Part 1 — What must be covered

Taken from Estonian course curricula (Keeltekeskus Kaja A1 and B1, Dialoog,
B-Lingua), which agree closely because they all track the same state standard.

### A1

| Topic | Estonian | Status |
|---|---|---|
| Alphabet, pronunciation, orthography | tähestik, hääldamine, ortograafia | — |
| Sentence structure | lauseehitus | — |
| Pronouns | asesõnad | — |
| **Question words** | **küsisõnad** | — |
| **Numerals** | **arvsõnad** | — |
| Pre/postpositions, conjunctions, adverbs | kaassõnad, sidesõnad, määrsõnad | — |
| Singular and plural | ainsus ja mitmus | forms exist |
| Affirmative and negative | jaatus ja eitus | drilled (negation → partitive) |
| **ma- and da-infinitive** | ma- ja da-tegevusnimi | tag exists, no drills |
| **Noun declension** | käändsõna käänamine | forms exist, no drills |
| **Present and simple past** | olevik, lihtminevik | forms exist, partial drills |
| **Imperative and conditional** | käskiv ja tingiv kõneviis | forms exist, no drills |

### B1 (adds)

| Topic | Estonian | Status |
|---|---|---|
| Declension sg + pl **with agreement** | ühildumine | forms exist; agreement untested |
| Compound words | liitsõnade moodustamine ja käänamine | — |
| **Comparison of adjectives** | võrdlusastmed | — |
| Cardinal and ordinal numbers | põhi- ja järgarvud | — |
| **Four past tenses** | liht-, enne-, täisminevik | only lihtminevik |
| Expressing the future | tuleviku väljendamine | — |
| **Participles** | kesksõnad | forms exist |
| Compound verbs | ühendverbid | — |
| **Impersonal voice** | umbisikuline tegumood | forms exist |
| Word order | sõnajärg | tag exists, no drills |
| Punctuation | kirjavahemärgid | — |
| **Verb government** | rektsioon | tag exists; sonapi has the data |

**Honest gap:** the app currently drills **two** of roughly twenty-five topics —
object case and irregular verb stems. Those were the right two, because they are
what the error log documents. But "everything a textbook teaches" is an order of
magnitude more, and most of it is *generatable*, because Vabamorf already
produces every form involved.

---

## Part 2 — What the research says (the parts I did not know)

### Blocked first, then interleaved — not one or the other

The strongest and most actionable finding. Interleaved practice (mixing rules)
beats blocked practice (drilling one rule) for **long-term accuracy** — but
**interleaving alone is an undesirable difficulty for novices**, and blocked
practice in the early phase is what builds the declarative knowledge in the
first place.

So the schedule is not a preference, it is a sequence:

```
new topic  →  BLOCKED drills until mastery  →  item joins the INTERLEAVED review pool
```

This maps exactly onto machinery that already exists: blocked = the drill
generator filtered to one rule; interleaved = the FSRS queue, which naturally
mixes everything due.

### Mastery thresholds, not lesson completion

Advancement is gated on demonstrated accuracy, not on having seen a page. The
standard shape is *n correct out of the last m attempts*, which is also what
makes "skip what I know" honest — the same check answers both questions.

### The prerequisite graph is unusually strong in Estonian

Not an arbitrary ordering. **Every case except nominative and partitive is built
from the genitive stem**, so `gen-stem` genuinely precedes `loc-case`,
`obj-case`, plurals and comparison. Getting the genitive wrong breaks eleven
other cases downstream. A knowledge graph here encodes a real dependency, which
is why topic order can be derived rather than hand-sequenced.

### Adaptive placement (IRT) is how "skip" is done properly

Ask progressively harder items until the learner fails; the level where they
fail is the entry point. This is one mechanism serving two features — placement
and skipping — and it needs a calibrated item bank, which generated drills give
for free.

### Duolingo's HLR — noted, not adopted

Half-life regression, open-sourced, 45 % better recall prediction than Leitner.
But **FSRS-6 is newer, better benchmarked and already integrated**. Recording it
here so the decision is deliberate rather than accidental.

### How Keeleklikk teaches both at once

16 thematic chapters — greetings, food, family, shopping, health, work. Grammar
is introduced **in service of a topic**, not as a separate track: the chapter
that needs the partitive teaches the partitive. That is the answer to "how do we
learn grammar and words simultaneously" — the theme is the unit, and it carries
both.

We can do this better than a fixed course, because our vocabulary is already
CEFR-tagged and topic-taggable, and drills are generated: a lesson becomes
**grammar rule × themed word set**, so drilling *täissihitis* with food
vocabulary teaches the rule and the words in the same repetition.

---

## Part 3 — Gap analysis against what exists

| Need | Have | Missing |
|---|---|---|
| Grammar topics | 2 of ~25 | 23 topics as drillable rules |
| Forms for those topics | **all of them** (411 349, gold-validated) | nothing |
| Explanations | 7 rules → EKK handbook | ~18 more mappings |
| Blocked practice | drill generator with rule filter | mastery gate |
| Interleaved practice | FSRS queue | feed from lessons |
| Progress / resume | review DB, vocab statuses | no lesson-level state |
| Skip known material | — | placement check |
| Quizzes | drills grade themselves | no unit checkpoint |
| Grammar + vocab together | separate | topic tagging on vocabulary |

The encouraging half: **the hard part is done.** Forms are generated and
validated, scheduling works, explanations link to the authority. What is missing
is mostly *curriculum metadata* — declaring the topics, their prerequisites and
their templates — rather than new machinery.

---

## Part 4 — The plan, in order

Each step is independently useful and shippable.

### 1. Topic model
`eesti/curriculum.py` — declare each topic: id, CEFR level, Estonian name, EKK
reference, prerequisites, and which generator produces its drills. Ship the
A1 set first. **No UI. This is the spine everything else hangs on.**

### 2. Generators for the big topics
Extend the drill generator to cover, in order of exam weight: noun declension
(all 14 cases), the four past tenses, imperative and conditional, ma-/da-
infinitive, comparison, numerals, question words. Vabamorf already produces
every form; this is templates plus explanations.

### 3. Mastery and progress
Per-topic state: attempts, rolling accuracy, `mastered_at`. Gate advancement on
*n of last m*. Persist where the learner left off. This is what makes it a
course rather than a drill box.

### 4. Placement / skip
Reuse the mastery check as a test-out: answer a short set correctly and the
topic is marked known without doing the lesson. Same mechanism, two features.

### 5. Blocked → interleaved handoff
On mastery, a topic's items enter the FSRS queue. Practice becomes review
automatically, and the research-backed schedule falls out of the existing parts.

### 6. Thematic lessons (grammar × vocabulary)
Tag vocabulary by theme; a lesson pairs a grammar rule with a themed word set.
Keeleklikk's insight, but generated, so themes and rules can be recombined.

### 7. Path and library split
Implement the two-surface structure in `app-structure.md`: a mastery-gated path
for grammar, a browsable library for material. Keelekõdi and the audio-only
episodes belong to the library — 30 minutes of mixed content with no transcript
is exposure, not a curriculum step.

### 8. Frequency-ordered vocabulary
Speakly's ordering, using the `freq_rank` already in the word list: progress
measured as "known within the top N", not as a percentage of the language.

### 9. Unit checkpoints
A short mixed quiz at the end of each level — interleaved by construction, and a
progress signal the learner can trust.

---

## Part 5 — Deliberately not doing

- **Hand-writing lesson prose.** EKK is the reference; we link to it.
- **Half-life regression.** FSRS is better and already in.
- **A fixed linear course.** The prerequisite graph gives order where order is
  real, and freedom everywhere else.
- **Gamification.** Same reasoning as `roadmap.md`: streaks retain, they do not
  teach.
