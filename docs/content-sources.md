# Where grammar and vocabulary actually come from

Two questions worth answering properly, because the obvious answers are wrong.

## Grammar: link to the authority, don't rewrite it

Keeleklikk and Keeletee are the well-known Estonian courses, and neither helps
here — they are **courses, not references**, and neither exposes an API. Looking
for "the grammar API" is the wrong search.

The authority does exist, free and online: **Eesti keele käsiraamat** (EKK), the
Estonian Language Institute's handbook by Erelt, Erelt and Ross, at
`arhiiv.eki.ee/books/ekk09/`. It has stable per-section URLs and — this is the
part that matters — **its syntax chapter numbers exactly the rules this app
drills**:

| EKK | Section |
|---|---|
| SÜ 36 | Sihitis |
| **SÜ 37** | **Täis- ja osasihitis** ← the documented gap |
| SÜ 38 | Täis- ja osasihitise valiku probleeme |
| SÜ 39 | Täissihitis omastavas või nimetavas käändes |
| SÜ 41 | Täissihitis käsklauses |

So `eesti/grammar.py` maps each error tag to its handbook section rather than
restating the rule. Three reasons that is better than writing our own:

1. **It is authoritative.** A learner who doubts a drill can check the source.
2. **It uses the exam's terminology.** What the error log calls `obj-case` is
   properly **täissihitis** (total object) vs **osasihitis** (partial object).
   Those are the words an examiner uses; teaching our own shorthand instead
   would be a small, permanent handicap.
3. **It cannot drift.** We are not maintaining a parallel grammar that slowly
   disagrees with the real one.

Seven tags are mapped: `obj-case`, `verb-form`, `gen-stem`, `gradation`,
`loc-case`, `rektsioon`, `ma-da-inf` — the same vocabulary as the Notion log.

Also noted but not used: **EKIToolkit**, a JavaScript module for embedding EKI
resources in a page. Worth revisiting if inline dictionary popups are ever
wanted, but it solves a presentation problem we do not have.

## Vocabulary: generate the forms, do not collect them

The instinct is to find a card bundle — an Anki deck, a Quizlet set, an export
from Sõnastik. **That is the worse option**, and the reason is specific to
Estonian.

Estonian words are learned as **põhivormid**, the three principal forms:

```
raamat, raamatu, raamatut          sõber, sõbra, sõpra
pood, poe, poodi                   tuba, toa, tuba
```

Nominative, genitive, partitive. Every other case is built from the **genitive
stem plus an ending**, so the trio *is* the word — learn it and you have all 14
cases; learn only the nominative and you have almost nothing.

We generate that trio from Vabamorf on demand, and it agrees with TalTech's
native-curated gold forms **98 % of the time** (`cli validate`). Compare:

| | card bundle | generated |
|---|---|---|
| coverage | a few thousand hand-made entries | every word Vabamorf knows |
| forms | whatever the author typed | synthesized, gold-validated |
| new words | someone must make a card | already there |
| storage | a file to keep in sync | none |

So: **no per-word storage, no bundles.** `lookup.principal_forms()` returns the
citation string a textbook would print, and `data/edge.db` holds the 411 349
pre-computed forms for the edge runtime — generated at build time, not curated.

The one thing generation cannot give is **meaning**: definitions, usage examples
and translations. That is what `api.sonapi.ee` is for (single lookups only), and
what the enriched Ekilex wordlist supplies for CEFR level and frequency.

### What Sõnaveeb and Sõnastik do and don't give

Both display the principal forms — they read the same Ekilex data — but neither
offers a bulk export a third-party app may use. Sõnaveeb's maintainers
explicitly ask people not to batch-request it. The sanctioned route is an Ekilex
API key, and the enriched wordlist already removes the need for one.

### Reconsidered: "the wordlist removes the need" was half true

It removed the need for **levels and frequency**, which is what it carries. It
did not remove the need for **meaning**, because it has none — and neither did
anything else here. The app knew 160 316 words, could inflect every one of them,
and could not say what a single one meant.

That is not academic. Twelve generated B1 object-case drills come back on
`etendus`, `luuletus`, `rahakott`, `kingitus`, `kleit`; a live corpus set drew
`hooldustöö` and `riigivisiit`. A learner supplies the right partitive, is
marked correct, and has practised morphology on a token. The scope of this
project is *learning Estonian*, not only sitting the exam, so that gap matters
more than the tidiness of "don't rebuild what exists".

**What changed, and what did not.** Sõnaveeb is still never batch-requested and
there is still no bulk helper. What changed is that answers are now *kept*:
`eesti/gloss.py` stores each lookup in `vocab.db`, which the state snapshot
carries. So a word is asked about **once, ever** — which is a stricter reading of
"do not hammer our server" than the code managed before, not a looser one.

Before this, `sonapi`'s cache sat in `data/cache/`: git-ignored, not the content
volume, not in the snapshot. Cloud Run scales to zero, so every cold start began
with an empty cache and re-requested every word the learner looked at — and
spaced repetition guarantees the same words come back. The module whose central
promise is "single lookups only" had storage that made it re-ask forever.

Three things keep this from drifting into a harvest, in code rather than in
prose: lookups happen only for a word in front of the learner (a card being
read, or a drill just answered); `sonapi` still spaces live requests a second
apart under a lock; and `gloss.DAILY_BUDGET` caps new words per day. At that cap
the full word list would take about three and a half years.

Licence: Ekilex is CC BY 4.0, so keeping a private copy of what one learner
looked up is squarely permitted. The store lives behind Access, travels only in
that learner's own snapshot, and is never redistributed — the same posture as
the ERR transcripts.

### Still available if bulk ever becomes necessary

Two sanctioned routes exist, both needing something only the account holder can
supply, so neither is wired up:

| Route | Gives | Needs |
|---|---|---|
| **Ekilex API** (`ekilex.ee`, key from the user profile page) | the whole database, CC BY 4.0, commercial use unrestricted | a free account and an API key |
| **EKI downloads** (`arhiiv.eki.ee/litsents/`) | *Eesti-vene sõnaraamat* (XML, CC BY 4.0) and the **A1/A2/B1 level word lists** (2018, CC BY 4.0) | Estonian ID-card authentication |

The second is the interesting one for this app: an official Estonian-Russian
dictionary and the exam board's own level vocabulary, both openly licensed. Worth
fetching if the learner wants glosses for words they have not met yet rather than
only the ones they have.
