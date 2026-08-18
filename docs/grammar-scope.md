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
| `obj-case` | ✅ built — genitive vs partitive under aspect/negation | Vabamorf synthesis |
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
