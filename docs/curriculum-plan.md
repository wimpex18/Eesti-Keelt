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
| Grammar topics | **declared: 36; drillable: 21** | 15 generators |
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

**Comparison, numerals and question words are built** — `eesti/patterns.py`,
`cli patterns`. That finishes every generator step 2 named. **21 of 36 topics**
now have practice.

Each needed a different treatment, and the interesting one is comparison.
Vabamorf will not synthesise it: ask for the comparative of `suur` and it
returns nothing, because Estonian comparatives are separate lemmas in its
lexicon. The rule — genitive stem + `-m` — is easy to write and dangerous to
trust: it gives `suurem` and `väiksem` correctly, and also `vanam` for *vanem*,
`pikam` for *pikem*, and `omam` for a word with no comparative at all. So the
generated form must be **a lemma Ekilex knows** *and* **have been observed in a
corpus** (`freq_rank > 0`). The second gate is the one that earns its keep — it
removes `hullum`, `täiem` and `ainsam`, all productively well-formed and never
written. 96 comparatives survive at A1–B1; the rule's failures are dropped
rather than taught.

Numerals are not about forms but **government**: after a cardinal above one the
noun goes to partitive singular — *kaks raamatut*, not *kaks raamatud*. An A1
rule with an A1 error. The frame needed countable nouns (frequency order alone
produced *"Mul on kaks tähelepanu"*, two attentions), so it reuses the
object-case semantic pools rather than inventing a list.

Question words are a **genuinely closed class**, so a table of twelve is the
right representation, not a tax — and each entry names the confusion that
actually happens (`kus`/`kuhu`, `kes`/`mis`, `kellele`/`kellelt`), which is where
Estonian splits and Russian does not.

Four generators now exist, so the five things every item must do — show, grade,
name, reveal, link the rule — live in `eesti/item.py` rather than in four
diverging copies.

**The verb topics are built** — `eesti/conjugation.py`, `cli conjugate`.
Nine topics at once: `olevik`, `lihtminevik`, `taisminevik`, `enneminevik`,
`tingiv`, `kaskiv`, `ma-da-inf`, `kesksonad`, `umbisikuline`. **2 700 items** at
A1–B1 from Vabamorf synthesis alone.

`verbs.py` already drilled verbs, but only *irregular stems* — verbs where
stripping `-ma` gives the wrong answer, so the distractor writes itself. That
deliberately skips every regular verb, which is right for stems and wrong for
everything else: a learner who can build `õpib` still has to choose between
`õpib` and `õppis`, `õpiks` and `õpib`, `pean õppima` and `tahan õppida`.

So the distractor here is **the same verb in the neighbouring form it gets
confused with** — `õpiks` against `õpib`, `tehtud` against `teinud`,
`tehakse` against `teeb`. What is tested is the marker, not the stem, and both
halves come from Vabamorf rather than a table. Where a verb produces the same
string for both, the item measures nothing and is dropped.

Two things the frames had to get right. They are **object-free**: the first
version wrote the impersonal as *"Seda ____ iga päev"*, and `seda` is a
partitive object — fine for `tegema`, ungrammatical for `liikuma`, with no
transitivity flag in the data to filter on. A locative frame (*"Siin ____ iga
päev"*) works for both, which avoids the per-verb semantic pool the object-case
templates have to carry. And the verb pool is **frequency-ordered**, because a
bleached frame reads fine with a verb met daily and uselessly with a rare one —
*"Hirmutage palun kohe!"* is grammatical and worthless.

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
`mitmus` all gained a generator at once. With rection, the verb topics and the closed classes, generators go
**2 → 21 of 36**.

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

**Step 2 is complete** for everything it named. What has no generator is what
the plan never claimed one for: the reference topics (`tahestik`,
`lauseehitus`), the closed word classes already covered by vocabulary work
(`asesonad`, `kaassonad`, `sidesonad`, `maarsonad`), and four topics that need
sentence-level machinery rather than form generation — `sonajark`,
`kirjavahemargid`, `uhildumine`, `liitsonad`. Those are honest gaps, listed
here so they are not mistaken for oversights.

### 3. Mastery and progress — done ✅
`eesti/progress.py`, plus `cli practice` (a graded session that records what
happened) and `cli progress` (where you stand on all 36 topics).
`eesti/practice.py` maps a topic to whichever of the six generators owns it, so
the learner asks for the conditional rather than for a generator.

Three decisions worth stating, because each has a plausible opposite:

- **Rolling window, not lifetime accuracy.** 8 of the last 10, and the window
  must be *full* — three clean answers is not evidence about a paradigm. A
  learner who got their first twenty wrong and their last twenty right has
  learned the topic; a lifetime ratio would say 50 % forever and never let them
  past.
- **The window must also cover five different items.** Without that the gate
  can be cleared by answering the same two items five times each: ten attempts,
  eight correct, window full, mastered — having demonstrated nothing about the
  paradigm and everything about short-term memory. `item_key` was already being
  stored and was never read, which is exactly what made the hole invisible. A
  real ten-item session produces ten distinct items, so this costs an honest
  learner nothing.
- **Mastery is never revoked.** A later bad run lowers current accuracy and
  brings items back through FSRS, but it does not clear `mastered_at`.
  Prerequisites unlock the rest of the syllabus, and revoking them would let one
  bad evening lock the learner out of half the course. Forgetting is the
  scheduler's job; sequencing is this module's, and wiring them to fight helps
  nobody.
- **Skipping and passing are one operation**, differing only in a `via` column.
  That is what lets step 4's test-out reuse this gate rather than build a
  parallel one.

**And it caught a live defect in the syllabus.** Topics with no generator —
`pohivormid`, `lauseehitus` — cannot be *demonstrated*, so requiring them made
everything downstream permanently unreachable: the path offered `tahestik` on
repeat and `gen-stem` never. A topic that cannot be tested cannot be a gate, so
those show as `reference` and do not block. A test now asserts every drillable
topic is reachable, which is the kind of failure nothing on screen would reveal.

### 4. Placement / skip — done ✅
`eesti/placement.py`, `cli placement` and `cli test-out --topic X`. It owns no
state: a probe calls `progress.mark_mastered(..., via="placement")`, which is
exactly the promise step 3 made about skipping and passing being one operation.

**The bar is 5 of 5, against practice's 8 of 10.** That looks inconsistent and
is not — the two buy different things. Ten attempts with two mistakes is a
learner who worked through a topic and mostly holds it. Five attempts is thin
evidence being used to skip the work entirely, so the only defensible reading of
a wrong answer is "not yet". A false pass silently removes a topic from the
course *and* unlocks everything downstream; a false fail costs one session of
practice the learner did not strictly need. The errors are not symmetric, so the
thresholds should not be either.

Probe attempts are recorded as ordinary attempts, because that is what they are
— a failed test-out means those items really were answered, and the rolling
window should know.

**It is not IRT, and the code says so.** The plan floated item-response theory:
ask progressively harder items, and where the learner fails is the entry point.
The adaptive half is here — the sweep walks study order and stops after two
consecutive failures — but the psychometric half is not, because IRT needs
per-item difficulty estimated from a population of test-takers and this app has
one user. Calling a stopping rule "IRT" would be dressing up a heuristic. What
the sweep actually leans on is the prerequisite graph: study order already
encodes difficulty, because a topic depending on four others is genuinely later.

**Failing one topic no longer ends the sweep.** The first version stopped after
two consecutive failures, and that was wrong in a way worth recording because it
looked reasonable. The syllabus is a **graph, not a line**: `osastav` and
`mitmus` are nouns, `olevik` and `verb-form` are verbs, and they are
independent. A learner solid on verbs and shaky on nouns — an ordinary way to be
— failed two noun topics in a row and the sweep concluded it had found their
level *without ever asking about a verb*.

A failure now prunes exactly what the graph says it should: the topics that
**depend on** the failed one. Failing `osastav` means not asking about `eitus`
or `obj-case`, which are built on it; it means nothing about the verb branch,
which keeps being probed. Measured on a learner who knows verbs and not nouns,
the sweep now reports `gen-stem, osastav, arvsonad` as entry points and marks
`olevik, verb-form, lihtminevik, ma-da-inf, kusisonad` known — where before it
stopped after two probes.

So the result is a **set** of entry points, which is the honest shape: one
"you are here" cannot say that someone is at A2 on verbs and A1 on nouns. Two
budgets bound the session (`MAX_FAILURES`, `MAX_PROBES`); they are stopping
rules for the learner's patience, not claims about their level.

### 5. Blocked → interleaved handoff — done ✅
`eesti/handoff.py`, plus `cli review`. `progress.py` decided when a topic was
learned and `review.py` decided when it needed seeing again, and nothing
connected them; this is the arrow.

**Two arrows, in fact.** On failure, an item enters the queue *already graded
wrong*, so FSRS schedules it soon rather than as fresh material — `mining.py`
did this for object-case and verb-form drills, and it now works for all six
generators. On mastery, a **sample** of the topic's items joins the queue, not
all of them: a topic can generate hundreds, and a queue that spikes every time
something is passed is one the learner stops opening.

**Interleaving turned out not to fall out for free, which was the assumption.**
Measured after building it: seeding three topics and asking for the queue
returned six `kusisonad`, then six `olevik`, then six `tingiv`. Blocked review,
produced by the module whose entire purpose is to end blocked review.

The cause is the batching. Six items enter the instant a topic is mastered, so
they carry near-identical due times, and `ORDER BY due` hands them back in the
order they went in. `review.interleave` now deals the due queue round-robin by
topic, keeping each topic's own order — and `due()` over-fetches before
truncating, because applying `LIMIT` first takes the ten most overdue, which are
the ten that entered together, which is one topic, leaving nothing to mix. That
second half was caught by a test written for the first.

Mixing here rather than in the scheduler is deliberate: FSRS decides *when* an
item returns and is good at it, and nothing about an answer changes if two items
due the same minute swap places. Selection stays the scheduler's; only the order
within what is already due is ours. A request for a single topic is a deliberate
drill-down and is left alone.

`pending_handoffs` exists because the handoff can be missed: a topic mastered
before this module existed, or in a session that ended early, would otherwise
sit outside the review pool forever. `cli review` sweeps for those first.

**And it exposed a seam.** `drills.Drill` — the object-case and verb-form
generators, the two the app started with — predated the curriculum model and
carried no `topic`, so the handoff crashed on exactly the two topics that matter
most. Both now declare their topic and share `item.py`'s interface with everyone
else.

### 6. Thematic lessons (grammar × vocabulary) — done ✅
`eesti/themes.py`, `cli themes`, and `practice --theme`. **Eleven themes, 233
words**, all validated against Ekilex.

Keeleklikk's chapters are *situations* — food, family, work — and grammar
arrives in service of one: the chapter that needs the partitive teaches the
partitive. Because everything here is generated, theme and rule stay **separate
axes and recombine freely**: `lihtminevik × reisimine`, `täissihitis × toit`.
Sixteen chapters becomes eleven themes × twenty-one drillable topics, from the
same generators, with no lesson written.

The word lists are hand-picked, and that is right — "which words belong to
*food*" is a curatorial judgement, and Keeleklikk's authors made it by hand too.
What is not left to judgement is whether the words are **real**: every lemma is
checked against the 160 316-word list, and the check immediately earned itself
by rejecting `kindad`, `kingad`, `saapad`, `sokid` — plural-only forms where the
lexicon lists `kinnas`, `king`, `saabas`, `sokk`, and whose genitive a generator
would have invented.

Two things the first working version got wrong, both visible only in the output:

- *"Mul on kaks riisi"* — two rice. Countability is not in the word list and is
  not guessable from the theme either: `toit` holds both `kook` and `suhkur`.
  An explicit `UNCOUNTABLE` set fixes it, tested to contain nothing stale.
- *"Mul on kaheksa reit"* — see below. That one was not a theme bug at all.

**And it exposed a real defect in the foundation.** `reis` produced `reit`,
which is the partitive of *reis* meaning **thigh**, not journey. The cause was
in `morph.case_forms`, which every drill and the whole exported dataset rest on:
when Vabamorf returned several validated candidates it broke the tie by
preferring the one with the fewest competing lemma readings. That is right for
`kool` (*kooli*, not *koola*) and exactly wrong for `reis`, because the rarer
word is the less ambiguous one. Two real words spelled the same cannot be
separated by morphology — only by meaning — and the same applies to free
variants like `kaht`/`kahte`, where a drill accepting one marks the other wrong.

`case_forms` now treats *several* candidates the way it already treated *none*:
it reports nothing. Measured cost, **111 of 2 570 A1–B1 nouns (4.3 %)** — and
every one of them would otherwise have been an exercise with a confidently wrong
answer.

### 7. Path and library split — done ✅
`eesti/library.py` (`cli library`) and `eesti/overview.py` (`cli status`).

The library is the second surface: **unordered, ungated, measured by exposure
only**. Keelekõdi forces the distinction — 30 minutes of mixed content with no
transcript is genuinely useful exposure and genuinely useless as a curriculum
step, because it cannot be sequenced, gated on or checked. Putting it on the
path would break the path's one promise, that finishing a step means something.

Exposure is counted as openings and minutes, and reports **no percentage**,
because no denominator would be honest: the library grows, and "12 % of the
library" says nothing about whether the learner can read. Whether a text is
worth their time is already answered by `vocab.py`, which measures words.

`browse(..., public_only=True)` filters on the **source's** licence rather than
on the item, so a new source cannot leak by forgetting to tag its rows. Today
that filter returns **0 of 421 items** — ERR is © ERR, Selges keeles carries no
reuse grant — which is not a bug but the reason Cloudflare Access is not
optional.

`cli status` prints all five sections with **no overall percentage**. That is a
decision, not an omission: the exam scores four parts separately and fails you
for a zero in any one, so a learner at "68 % overall" who has never done a
listening task is not 68 % ready, and an aggregate hides precisely the thing
that decides the outcome.

**Four defects found by auditing 7–9 afterwards**, in rough order of severity:

1. **Nothing ever wrote to the vocabulary database.** `vocab.set_status` and
   `record_encounter` existed, `coverage` and `band_progress` read them, and no
   caller anywhere put a word in — so step 8's bands and the reader's "how much
   of this text do you know" both measured a permanently empty table. The
   measurement had been built without the recording. `library.open_item` now
   records encounters when material is opened, and `cli vocab --know` is the
   explicit act that marks a word known. Encounters are deliberately **not**
   knowledge: a word skimmed past is not a word learned, and conflating them is
   what makes automatic "known" counts meaningless.
2. **Practice made a network call.** `items_for("rektsioon")` fetched EKK's page
   on demand; CI proved the cost by getting `403 Forbidden` from a runner, so a
   drill failed because someone else's server had a bad minute — in the project
   whose first architectural claim is that it does not do that. Rections are now
   fetched once by `cli rections`, stored, and *read* at practice time.
   `tests/test_offline.py` blocks sockets outright and runs every generator, so
   the claim is enforced instead of asserted.
3. **A multi-skill library section could not reach its second skill.** `browse`
   asked each skill for `limit` rows and truncated, so with eight writing tasks
   and a limit of five, no speaking task was ever visible. Now dealt round-robin.
4. **Two library openings in the same second lost their minutes.** The exposure
   key was `(item_id, seen_at)` at second granularity, so the second `INSERT OR
   REPLACE` overwrote the first — and the test I had written *slept 1.05 s to
   avoid noticing*. A test that waits to observe correct behaviour is describing
   the defect, not the requirement.

### 8. Frequency-ordered vocabulary — done ✅
`vocab.band_progress`. Grammar is sequenced because it has real prerequisites;
vocabulary has none, only usefulness, so it is ordered by `freq_rank` in bands
of 500 up to 4 000 — roughly the whole A1–B1 target.

The denominator is the point. **"1 200 of the top 2 000" means something;
"12 % of Estonian" does not**, because the tail is endless and nobody is trying
to finish it. Unranked lemmas are excluded rather than pooled: `freq_rank` 0
means the frequency corpus never saw the word, which is not the same as it being
rare, and counting them would invent a denominator. Bands report their real
size — ranks are not dense, so the first band holds 304 words, not 500.

### 9. Unit checkpoints — done ✅
`eesti/checkpoint.py`, `cli checkpoint --level A1`.

A checkpoint asks across **every drillable topic at a level at once**, which
makes it the one thing here that is interleaved without having to be arranged —
there is no blocked version of "everything you learned at A1". That is also why
it measures something a topic gate cannot: the gate asks "can you do the
conditional" right after ten conditionals, when the rule is in working memory
and every item has the same shape. A checkpoint gives no clue which rule
applies, which is the situation the exam creates and the one in which people who
have mastered every topic separately find they cannot choose between them.

Items are dealt **round-robin, not sampled randomly**: a random draw from a
level with nine verb topics and three noun topics measures what the syllabus
happens to contain rather than the learner.

`weakest` **points rather than proves**: fifteen questions across eleven topics
is one or two items each, so it says where to look, not what the learner cannot
do. The CLI prints the tallies (`olevik 0/1`) rather than bare names, so the
sample size is visible instead of implied.

The pass mark is **75 %**, below the topic gate's 80 %. Not a contradiction —
the same number across a whole level unprompted is harder, so an equal bar would
make finishing a level rarer than mastering every topic in it. And a failed
checkpoint **un-masters nothing**; it puts the missed items in the review queue,
because its value is the diagnosis (`weakest` names the topics that went worse
than the level as a whole), not the score.

---

## Part 5 — Deliberately not doing

- **Hand-writing lesson prose.** EKK is the reference; we link to it.
- **Half-life regression.** FSRS is better and already in.
- **A fixed linear course.** The prerequisite graph gives order where order is
  real, and freedom everywhere else.
- **Gamification.** Same reasoning as `roadmap.md`: streaks retain, they do not
  teach.
