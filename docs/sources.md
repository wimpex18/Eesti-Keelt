# Sources

Source credits are served from `eesti.sources.REGISTRY` at `/api/sources` and
shown in **Allikad**. Library items link to their original source and describe
changes. Public visitors see shared learning material; personal imports stay
in the owner's library.

## Free educational use

Grove is free and non-commercial. Public educational material is welcome as a
source; in-app reuse follows the material's licence, permission or an applicable
exception, with attribution. Public access alone does not establish a right to
republish a complete document, recording or course. For example, [ERR's terms](https://info.err.ee/982667/kasutustingimused-ja-kommenteerimine)
distinguish private non-commercial use and linking from other reuse requiring
permission.

The ledger records current source access. Owner-only status can change after
the reuse basis is established; it is not a permanent product limitation.
Openly licensed resources should be shared within their terms rather than
restricted just because they were first imported by the owner.

## Language data

| Source | Used for |
|---|---|
| Vabamorf via EstNLTK | all forms, analysis, spelling — the answer key |
| Enriched Ekilex word list (KristjanPikhof) | 160 000+ lemmas, estimated CEFR, frequency rank |
| EKI *Eesti keele tasemete sõnavara* (`A1A2B1.txt`) | official A1/A2/B1 levels, outranks the estimate |
| EKI *põhisõnavara sõnastik* (PSV) | learner-level definitions, examples, rection |
| EKI *Eesti-vene sõnaraamat* (EVS) | offline Russian, inflection type, question-word cues, example phrases with Russian, public practice sentences |
| EKI *Võõrsõnade leksikon* (VSL), *seletav sõnaraamat* (EKSS) | fallback Estonian definitions |
| EKI *Haridussõnastik* (HAR) | fallback Russian for education terms |
| Ekilex API (EKI) | live word card with `EKILEX_API_KEY` |
| Sõnaveeb via `api.sonapi.ee` | live word card without a key |
| EKI *Eesti keele grammatika tabelid* (PSV) | case questions and endings, how forms derive from the principal forms, mood tables; restated in Russian on Reegel pages (`eesti/lessons.py`, `eesti/lessontext.py`) |
| EKI teatmik, *Asesõnade käänamine* | pronoun paradigms (`eesti/pronouns.py`) |
| *Eesti keele käsiraamat* (EKK) | own Russian explanations and short attributed examples link to their sections; SÜ 65 rection facts |
| EKI teatmik | pronoun declension facts with stress/stem marks removed; source linked in each lesson |
| EKI *põhisõnavara hääldused* | a native voice for word forms, with quantity and palatalisation (`cli import-haaldused`) |
| EKI *kõnekorpused* | sentences read aloud: dictation with a person instead of a synthesiser (`cli import-konekorpus`) |
| `data/seed_glossary.tsv` | 315 hand-written glosses for drill words |

Keep EKI attribution wherever EKI text is shown (`eesti.sources.REGISTRY`).

Sõnaveeb and Ekilex answers are stored once per word in `vocab.db`
(`gloss.py`) under a daily cap: the Russian, the definitions, the rection, the
muuttüüp and the sense's **usage examples**, which the card credits to whoever
wrote them. For more than the stored fields, link to Sõnaveeb
(`sonapi.entry_url`).

## EKI files (`deploy/eki/`)

Downloaded from <https://arhiiv.eki.ee/>, committed (XML gzipped) and
imported by the `Dockerfile` into `data/eesti.db`. `/api/health` reports actual
runtime dependency versions and the image's reference input fingerprints;
input presence is distinct from the imported row counts. The word-list download
pins an upstream commit and verifies SHA-256 (`eesti/reference.py`). Authenticated
EKI hashes identify the supplied bytes; they do not prove those bytes are the
newest upstream publication. These bulk dictionary files are imported locally; live Ekilex lookups and
the EKK rection page use separate request paths.

| File | Import | Rows |
|---|---|---|
| `A1A2B1.txt` | `cli import-levels` | 4 340 distinct lemmas with official level |
| `psv_EKI_CCBY40.xml.gz` | `cli import-psv` | 4 849 learner definitions |
| `evs_EKI_CCBY40.xml.gz` | `cli import-evs` | 60 672 lemmas with Russian; 8 question-word cues (`evs_question`); 137 316 example phrases and 1 912 idioms with Russian (`evs_example`) |
| `vsl_EKI_CCBY40.xml.gz` | `cli import-vsl` | 30 095 definitions |
| `har_EKI_CCBY40.xml.gz` | `cli import-har` | 5 905 terms with Russian |
| `ekss_EKI_CCBY40.xml.gz` | `cli import-ekss` | 117 937 definitions |

Lookup order — **Russian:** seed → live dictionary → EVS → HAR
(`eesti/meaning.py`). **Definition:** PSV → live → VSL → EKSS
(`eesti/api/grammar.py`), with native-level wording folded under *täpsem
seletus* when PSV answers. **Rektsioon, muuttüüp:** live, else PSV and EVS.
**Example phrases with Russian** (*Näited* on the word card): EVS only, every
phrase in EKI's order, three shown and the rest folded; the same phrases on
meaning cards in Järjekord (`evs.practice_phrase`); domain terms
(*zool*, *aj*…) and archaic renderings are left out.
**Public practice sentences** (DEV-54): the harvested corpus is owner-only, so
outside the owner's scope EVS's example phrases are the pool (`evs.phrases`):
examples only, never idioms, spelled out once (no slot, alternatives, ellipsis
or brackets), headword at the learner's levels on the word list. They feed
case gap-fill (`gen-stem`, `osastav`, `mitmus`, `kohakaanded`,
`harvad-kaanded`; the target word must itself be listed at those levels),
the comma drill, `sonajark` tiles (noun phrases whose order EKK fixes), dictation, read-aloud and the mock's
reading and listening sections. The owner's corpus comes first; EVS fills
what it cannot. Every such item shows *EKI eesti-vene sõnaraamat · CC BY 4.0*.
**Question-word cue** (`küsisõnad`): EVS only, the sense EVS illustrates with
a direct question (`docs/curriculum.md`). No other source in the repo has
Russian for question words: the seed has none, PSV, VSL and EKSS have no
Russian, HAR has no question words.

The XML has no root element and undeclared prefixes, one article per line
(`eesti/ekixml.py`). To refresh a file: download, `gzip -9 -n`, replace, run the
matching import with `--check`, commit.

## Reading and listening material

| Source | Used for |
|---|---|
| Selges keeles (WordPress.com API) | reading texts, cloze sentences |
| ERR *Lihtsad uudised* | weekly reading feed |
| ERR Raadio 4 language archives | grammar-lesson episodes: audio, transcripts filed as `grammatika` |
| HARNO exam material | past tasks and listening audio, downloaded by `cli harvest-exam --download` into `data/exam/` for private study, read in `Eksam`; never committed, always shown with the board's name |
| EIS public tasks | the task's own text and its recordings, read in `Eksam` (`cli harvest-exam --download`); scoring stays at EIS, which is the only place the answers exist |
| Own material (`cli ingest`) | owner-only |

Personal imported items are available only to the signed-in owner. Public
content reads filter source visibility before selecting items, files or drills.

The shared corpus is restored through the owner's Durable Object before both
guest and permanent learner requests. Guests keep separate progress and never
receive the owner's learner state.

Harvests merge by source URL and official level, retaining the first issued
item id and original addition date. A partial or empty refresh does not delete
other texts or levels; pointer-only and failed EIS fetches retain stored text,
recordings and files. Changed text invalidates its derived topic links.
Stored reading questions
check the current text; replacement questions use new indices, preserving the
event history without grading an old page against a new key. Item
metadata records catalogue check time and the SHA-256 of the retained content.
Selges pagination checks the advertised total and rejects repeated pages.
EIS and HARNO harvesting are independent, so either can refresh during an
outage of the other. Intentional source deletion removes its topic links.

HARNO downloads validate the file format before an atomic replacement;
`cli harvest-exam --download --refresh` rechecks existing files and keeps usable
copies when a request fails. The catalogue stores file size and SHA-256 for
valid local copies. A file hash identifies bytes, not their publication date.
Content uploads reject empty or damaged databases before replacing the usable
library. The Worker confirms corpus import before accepting the restored boot,
so a rejected import is retried. `cli push-content` rebuilds both
morphology-derived links and explicit
lesson-label links before uploading; it requires a built word list on the
publishing machine. `cli link-topics` remains useful for a local preview.
This analysis runs at publication, never in a learner request.

Public source checks exercise parsing as well as HTTP reachability: the
[Selges archive API](https://public-api.wordpress.com/rest/v1.1/sites/selgeskeeles.wordpress.com/posts/?number=1),
[ERR news](https://news.err.ee/k/lihtsad-uudised),
[ERR radio](https://r4.err.ee/755936/kak-jeto-po-jestonski-28),
[HARNO catalogue](https://harno.ee/eesti-keele-tasemeeksamid), and
[EIS public tasks](https://eis.harno.ee/publicitems) currently yield their
expected content shapes. EIS task text and recording links parse; this does
not establish playback of every recording or availability of deployed mounts.
The Sõnaveeb mirror returns a word result and authenticated Ekilex returns a
word ID. These checks are independent of the grammar model chain and do not
promise third-party uptime.

## Grammar evidence and evaluation

| Source | Used for |
|---|---|
| EVKK learner corpus (TLU) | ranking error tags |
| EstGEC-L2 (TLU) | attested word-order corrections |
| GiellaLT `lang-est-x-utee` | agreement exceptions |
| TalTech `inflection_et` | validating Vabamorf (`cli validate`) |
| TalTech `grammar_et` | second eval track (`evals/external.py`) |

## Services

TartuNLP TTS, translation and GEC (public University of Tartu APIs); model
providers in `docs/ai-providers.md`.

## Typeface and icons

| Asset | Where |
|---|---|
| Geologica (Monokrom) | `eesti/web/fonts/`, notices beside the files |
| HLS.js light player | `eesti/web/vendor/hls.light.min.js`, upstream notices alongside |
| Phosphor Icons | inlined in `eesti/web/js/icons.js`; notices beside the source |

These assets are served from this origin; the page asks no font or icon host for anything.

The ingestion/store/UI map and freshness boundaries are in
`docs/source-integrations.md`.
