# Grammar scope: beyond nouns

## Correcting the record

An earlier note said "for many words genitive and partitive are identical." That
framing was misleading. Measured against the indexed A1–B1 nouns:

| | count | share |
|---|---:|---:|
| genitive **≠** partitive (drillable) | 1 741 | **69 %** |
| genitive **=** partitive | 792 | 31 % |

**The majority differ.** The identical cases are real and must still be excluded
from drills — `kino`→kino/kino, `kostüüm`→kostüümi/kostüümi, `kets`→ketsi/ketsi
give the learner no way to be wrong — but they are the minority, not the norm.

Reproduce with:

```bash
.venv/bin/python -c "from eesti.wordlist import connect; c=connect(); \
print(c.execute('SELECT distinct_, COUNT(*) FROM object_cases GROUP BY distinct_').fetchall())"
```

## What Vabamorf can already generate

Verified — no new data source is needed for morphology. `synthesize()` covers
every part of speech, including the irregular stems that are gap #2 in the error
log:

| lemma | -n | -sin | -nud | -tud | -da |
|---|---|---|---|---|---|
| minema | lähen | läksin | läinud | mindud | minna |
| tegema | teen | tegin | teinud | tehtud | teha |
| sööma | söön | sõin | söönud | söödud | süüa |
| nägema | näen | nägin | näinud | nähtud | näha |
| lugema | loen | lugesin | loetud | loetud | lugeda |

Adjectives inflect too (`uus`→uue/uut, `kallis`→kalli/kallist), which matters
because an adjective must **agree** with its noun's case — a second, independent
way to get object case wrong that the current drills do not test.

All 14 cases are available (`sg n/g/p/ill/in/el/all/ad/abl/tr/ter/es/ab/kom`),
so the `loc-case` tag is generatable with the same machinery.

## Planned drill families

Each maps to a tag that already exists in the Notion `Vead` database, so results
group with the hand-logged history rather than starting a parallel taxonomy.

| Tag | Drill | Source of truth |
|---|---|---|
| `obj-case` | ✅ built — template frames for aspect, blended with corpus sentences under negation | Vabamorf synthesis + Selges keeles |
| `verb-form` | irregular stem: given lemma + tense/person, produce the form | Vabamorf synthesis |
| `ma-da-inf` | which infinitive a governing verb takes (`hakkan lugema` / `oskan lugeda`) | curated + sonapi `rection` |
| `rektsioon` | which case a verb governs | **sonapi `rection` field** |
| `loc-case` | the 6 locative cases (sees/seest/sisse, peal/pealt/peale) | Vabamorf, all 14 tags |
| `gradation` | consonant gradation (`sõber`→sõbra/sõpra, `pood`→poe/poodi) | Vabamorf + inflectionType |
| `gen-stem` | genitive stem changes | Vabamorf + inflectionType |

## Grammar data sources, ranked

**1. Vabamorf / EstNLTK — offline, primary.** Labelled, deterministic, no
network. Round-trip validated. Already the backbone.

**2. `api.sonapi.ee` — online, enrichment.** Verified working, no auth:

```
GET https://api.sonapi.ee/v2/lugema
```

Returns 53 forms for a verb with Estonian morphology labels (`ma-infinitiiv`,
`da-infinitiiv`, `des-vorm`, `v-kesksõna`), plus three things Vabamorf does not
give:

- **`inflectionType`** — the muuttüüp number (`raamat`=2, `lugema`=28), which is
  the declension-type system the Notion "Nomenid A–F" page already tracks.
- **`rection`** — e.g. `lugema` → `"mida, kust, kellele"`. This is the
  `rektsioon` tag, directly.
- **definitions, usage examples and EN/RU translations.**

⚠️ Treat as strictly optional and **single-lookup only**. It is a third-party
surface over Sõnaveeb, whose maintainers explicitly ask people not to batch
request. Cache every response; never loop over a word list. If it disappears, the
app must lose only enrichment, never core function.

**3. Ekilex API — official, keyed.** ekilex.ee account → API key, CC-BY-4.0. The
sanctioned bulk route if enrichment ever needs to be pre-computed. Preferred over
sonapi for anything systematic.

**4. ÕS 2025** (`eki.ee/os-2025`) — ~60 000 headwords, the normative authority on
declension and conjugation. **No API** (EKI state this explicitly); it reaches us
indirectly through Ekilex/Sõnaveeb.

**5. Reference grammars** for writing rule explanations, not for data:
Wiktionary's Estonian conjugation appendix, `keeleweb2.ut.ee` (University of
Tartu, free A1–C1 exercises), `cooljugator.com/ee`.

## Diversifying vocabulary

The current drills draw on ~40 curated nouns across six semantic pools. That is
right for teaching the *rule* but narrow for vocabulary. The fix is **more pools**,
not a looser filter — pairing every frame with every noun is what produced
"Ma ostsin haigla ära" (I bought the hospital). Next pools: transport, housing,
work, health, documents/bureaucracy — the latter being disproportionately useful
for a residence-permit exam.

## The 23 rections, audited against ÕS-2025-era EKI — 2026-09-12

`cli rections` scrapes EKK SÜ 64, published 2009 and served from an *archive*
domain, and the app now asserts those 23 contrasts **normatively**: the
`rektsioon` drill marks an answer wrong, and `rection.errors` corrects free
writing. Meanwhile **ÕS 2025 became the basis of the written-language norm on
2026-01-01**, and EKI route current usage decisions through the ühendsõnastik
in Sõnaveeb. A contrast the norm had since revised would be taught stale, by
the most confident thing this app says.

So all 23 were checked, one lookup at a time through `sonapi` with its own 1 s
throttle — no bulk helper was written and none exists.

| | |
|---|---|
| agree with Sõnaveeb | 11 |
| **Sõnaveeb lists the starred form as an attested rection** | **7** |
| no rection field (the adjectives and the two phrases) | 5 |

The seven: `baseeruma`, `kaasuma`, `panustama`, `põhinema`, `rajanema`,
`sarnanema`, `tuginema`. In every one, the form SÜ 64 stars is the `-le`
allative, and Sõnaveeb lists it beside the recommended form under the *same*
sense, with nothing marking it as second-best.

**The teaching is unchanged, because it is still EKI's.** Their keelenõuanne
says what the handbook says — `põhinema` takes `millel`, while `toetuma` and
`tuginema` take `millele` — and Emakeele Selts has a paper on exactly this
drift (*"Kas käbi sarnaneb kännule või kännuga? Alaleütleva käände
pealetungist"*). Sõnaveeb's `rection` field is descriptive: it records the
patterns that occur, not the one to use.

**The wording changed, because "требует" was stronger than EKI is.** Calling
the other form simply wrong, when EKI's own dictionary records it, is the same
overreach the V2 explanation already avoids by saying *обычно* rather than
*всегда* — stating a strong recommendation as a rule teaches a harder rule than
the source does, and the learner then "corrects" Estonian that natives write.
`RECTION_WHY` now says EKI recommends, notes that the `-le` form is written
too, and says the exam marks by the recommendation. Which is the true and
useful thing, in that order.

Re-check when a new ÕS lands, or if EKK moves off `arhiiv.eki.ee`. The audit
is twenty lines of throwaway script against `rection.load()`; it is not worth a
CI job, and running it needs 23 requests to somebody else's server.
