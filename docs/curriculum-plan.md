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

### The priority order was one person's, and now it does not have to be

Every weighting in this project came from a single error log. EVKK — Tallinn
University's corpus of learner Estonian, annotated by linguists — publishes
corpus-wide counts for its error taxonomy, and `eesti/harvest/evkk.py` now reads
them. **51 467 annotated errors**, ranked into our nine tags:

| Tag | Marks | Share |
|---|---:|---:|
| `vocab` | 12 437 | 24.2 % |
| **`word-order`** | **5 889** | **11.4 %** |
| **`rektsioon`** | **5 170** | **10.0 %** |
| `verb-form` | 2 382 | 4.6 % |
| `gen-stem` | 1 566 | 3.0 % |
| `ma-da-inf` | 1 152 | 2.2 % |
| `loc-case` | 833 | 1.6 % |
| **`obj-case`** | **653** | **1.3 %** |
| `gradation` | 434 | 0.8 % |
| *(unmapped)* | 20 951 | 40.7 % |

Object case — the thing this app was built around — is **1.3 %** of annotated
learner errors. The two largest are word order and verb rection: the first has a
tag and no model behind it, the second has a tag, no drills, and (since `sonapi`
was wired) all the data it needs.

**This does not demote the error log.** The log is evidence about *this* learner,
gathered by the person who has to sit the exam, and it stays the first weight —
a corpus average is the wrong thing to study if your own mistakes are elsewhere.
What it does is remove the assumption that one ranking generalises, which is what
was quietly driving topic order.

Two honest caveats. These are **annotation** frequencies: a parent category
absorbs marks a finer child would have taken (`põhikäänded` alone carries 1 331),
and 40.7 % falls outside our nine tags entirely, mostly spelling and text-level
categories we do not model. And the corpus leans on exam essays, where word order
and register errors are more visible than in speech. Read the ordering, not the
numbers.

**Consequence for Part 4:** step 2's generator order changes. `rektsioon` moves
to the front — it is the second-largest real error class and the data is already
on hand — and word order becomes a topic that needs modelling rather than a tag
that exists.

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
| Grammar topics | **declared: 36; drillable: 8** | 28 generators |
| Forms for those topics | **all of them** (411 349, gold-validated) | nothing |
| Explanations | 8 rules → EKK handbook, verified | ~17 more mappings |
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

### 1. Topic model — done ✅
`eesti/curriculum.py` declares **36 topics** across A1/A2/B1: id, level, Estonian
and Russian names, prerequisites, error tag, and which generator drills it.
`python -m eesti.cli curriculum` prints the path.

All three levels shipped rather than A1 alone — the topics are declarative data,
and a partial graph would have produced a prerequisite order that looked
authoritative while missing half its edges.

Two things came out of building it that were not in the plan:

- **Sequencing and priority are different questions**, and merging them produced
  nonsense. Ordering the path by corpus error weight put irregular verb stems
  before the genitive stem and left the alphabet until last. So `order()` derives
  the *study path* — graph first, then the authored course sequence — and
  `practice_order()` ranks the *same topics by where learners fail*. The graph
  stays the hard constraint in both: nothing can teach a case before the stem it
  is built from, and a test asserts it.
- **Six of the seven handbook references pointed at the wrong section.** EKK
  numbers its morphology chapter `M`, not `MO`, and its sub-pages do not run in
  section order, so every morphology link resolved to a real page carrying a
  different rule — which is worse than no link, because it looks checked. All
  eight are now read off the handbook's own contents and pinned by test.
  `word-order`, the largest error class in the learner corpus, had no entry at
  all and now has one (**SÜ 90**); `rektsioon` moved from SÜ 43 to **SÜ 64**,
  which is titled *"Rektsioone, milles sageli eksitakse"*.

### 2. Generators for the big topics
Extend the drill generator, in an order the corpus evidence now sets rather than
guesswork: **rektsioon** (largest real error class with drillable data, straight
from `sonapi`), noun declension (all 14 cases), the four past tenses, ma-/da-
infinitive, imperative and conditional, comparison, numerals, question words.
Vabamorf already produces every form; this is templates plus explanations.

Two inputs, not one. Templates give controlled contrasts; **cloze deletion over
the 349 harvested Selges keeles texts** gives authentic sentences whose answers
are correct because a native wrote them (see `roadmap.md`). Prefer the corpus
where it has the pattern; fall back to templates where it does not.

**`rektsioon` is built** — `eesti/rection.py`, `cli cloze --rule rection`.
The source is not a dictionary dump: **EKK SÜ 64 is titled "Rektsioone, milles
sageli eksitakse"** — *rections that are often got wrong* — and it tabulates
headword, correct case frame, and the wrong one, starred. An authority's own
error list, one page, fetched once. So the distractor is a documented error
rather than a decoy, the same standard the verb-stem drills hold to.

`providers/sonapi.py` could supply rections in bulk and deliberately does not:
its own docstring says single lookups only, because Sõnaveeb asks not to be
batch-requested, and reinterpreting that rule the moment it became convenient
is how such a rule dies. It stays interactive, enriching a word the learner is
looking at.

62 entries; 23 survive as unambiguous contrasts; **6 are A1–B1** (17 including
B2, available with `--levels`). Small, and honestly so — the refusals are the
point:

- *`sarnane mille/millega (*millele)`* — **two correct frames**, so a drill
  accepting one marks the other wrong. Dropped.
- *`kindel milles (*millele) kellele ~ kelle peale`* — stars the allative for
  things, then licenses it for people. A contradiction, not a contrast. Dropped.
- *`algama millal`*, *`kohustus kelle vastu`* — real rules, but not case
  contrasts. Dropped rather than forced into a case slot.

**These are generated from a frame, not from the corpus**, which inverts the
choice made for case forms — for a reason worth recording. A corpus is
authoritative about case *forms*, because morphology is not something a
journalist gets wrong. It is **not** authoritative about case *choice*: searching
the 2 073 harvested sentences for these verbs returned three hits, and one was
*"süsteem põhineb kaartidele"* — the exact error EKK stars under `põhinema`, in
published simplified news. Mining it would have taught the mistake as the answer.

**The corpus half is built** — `eesti/cloze.py`, `python -m eesti.cli cloze`.
2 073 usable sentences yield **1 138 case items and 28 negation items** across
five topics, so `gen-stem`, `osastav`, `kohakaanded`, `harvad-kaanded` and
`mitmus` all gained a generator at once. With rection, generators go **2 → 8 of 36**.

The design problem was not extraction, it was **deciding when an authentic
sentence has one right answer.** Blank the object in *"Ta luges raamatut"* and
ask genitive-or-partitive, and you assert the genitive is wrong — which depends
on telicity, which Estonian frequently leaves open. Marking a licit answer wrong
teaches a rule that does not exist, which is worse than not drilling at all. So
an item ships only where the form is forced, by one of two routes:

| Route | Why the answer is unique |
|---|---|
| **The prompt names the case** — *"Ma elan ____ (Tallinn, seesütlev)"* | Morphology decides. Nothing is claimed about which case the sentence needed; the learner produces a form, which is the skill the error log records. |
| **A trigger makes the case obligatory** — negation | Under negation the partitive is exception-free. This is the one object-case rule needing no aspect judgement, and the only one generated from the corpus. |

Three gates run before any item ships: the token must read as **one** lemma
(naming it in the prompt is what pins the answer), Vabamorf must **synthesise
the attested form back** from lemma + case (disagreement means something is
wrong and the item is dropped, not guessed at), and answer and distractor must
actually differ.

The distractor is chosen per case rather than uniformly: the citation form for
the genitive, the genitive for the partitive, and for every other case the
ending attached to the **nominative stem instead of the genitive stem** —
*sõber* + *-s* → *sõbers* where Estonian says *sõbras*. That is not a decoy, it
is the error, and it is why `gen-stem` sits upstream of eleven topics.

Also caught by building it: negation scopes over its **clause**, not the
sentence. The first version explained a partitive in one clause by an `ei` in
another.

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
