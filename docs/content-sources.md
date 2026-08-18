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
