# Sources

Every third party the app draws on. The ledger of record is
`eesti/licences.py` (`REGISTRY`), served at `/api/sources` and shown in
`Allikad`; `licence` and `redistributable` are columns, so every library item
can answer "may this be shown to anyone but the owner?".

## Language data

| Source | Licence | Used for |
|---|---|---|
| Vabamorf via EstNLTK | permissive | all forms, analysis, spelling — the answer key |
| Enriched Ekilex word list (KristjanPikhof) | CC-BY-SA-4.0 | 160 000+ lemmas, estimated CEFR, frequency rank |
| EKI *Eesti keele tasemete sõnavara* (`A1A2B1.txt`) | CC-BY-4.0 | official A1/A2/B1 levels, outranks the estimate |
| EKI *põhisõnavara sõnastik* (PSV) | CC-BY-4.0 | learner-level definitions, examples, rection |
| EKI *Eesti-vene sõnaraamat* (EVS) | CC-BY-4.0 | offline Russian, inflection type, question-word cues |
| EKI *Võõrsõnade leksikon* (VSL), *seletav sõnaraamat* (EKSS) | CC-BY-4.0 | fallback Estonian definitions |
| EKI *Haridussõnastik* (HAR) | CC-BY-4.0 | fallback Russian for education terms |
| Ekilex API (EKI) | CC-BY-4.0 | live word card with `EKILEX_API_KEY` |
| Sõnaveeb via `api.sonapi.ee` | Ekilex data CC-BY-4.0, third-party endpoint | live word card without a key |
| *Eesti keele käsiraamat* (EKK) | © EKI — linked, not reproduced | rule links per topic; SÜ 64 rection list |
| EKI *põhisõnavara hääldused* | CC-BY-4.0, owner-only | a native voice for word forms, with quantity and palatalisation (`cli import-haaldused`) |
| EKI *kõnekorpused* | CC-BY-4.0; the works read stay in copyright | sentences read aloud: dictation with a person instead of a synthesiser (`cli import-konekorpus`) |
| `data/seed_glossary.tsv` | own work | 294 hand-written glosses for drill words |

Keep EKI attribution wherever EKI text is shown (`eesti/licences.py`).

Sõnaveeb and Ekilex answers are stored once per word in `vocab.db`
(`gloss.py`) under a daily cap: the Russian, the definitions, the rection, the
muuttüüp and the sense's **usage examples**, which the card credits to whoever
wrote them. For more than the stored fields, link to Sõnaveeb
(`sonapi.entry_url`).

## EKI files (`deploy/eki/`)

Downloaded from <https://arhiiv.eki.ee/litsents/>, committed (XML gzipped) and
imported by the `Dockerfile` into `data/eesti.db`. These bulk dictionary files are imported locally; live Ekilex lookups and
the EKK rection page use separate request paths.

| File | Import | Rows |
|---|---|---|
| `A1A2B1.txt` | `cli import-levels` | 4 456 lemmas with official level |
| `psv_EKI_CCBY40.xml.gz` | `cli import-psv` | 4 849 learner definitions |
| `evs_EKI_CCBY40.xml.gz` | `cli import-evs` | 60 672 lemmas with Russian; 8 question-word cues (`evs_question`) |
| `vsl_EKI_CCBY40.xml.gz` | `cli import-vsl` | 30 095 definitions |
| `har_EKI_CCBY40.xml.gz` | `cli import-har` | 5 905 terms with Russian |
| `ekss_EKI_CCBY40.xml.gz` | `cli import-ekss` | 117 937 definitions |

Lookup order — **Russian:** seed → live dictionary → EVS → HAR
(`eesti/meaning.py`). **Definition:** PSV → live → VSL → EKSS
(`eesti/api/grammar.py`), with native-level wording folded under *täpsem
seletus* when PSV answers. **Rektsioon, muuttüüp:** live, else PSV and EVS.
**Question-word cue** (`küsisõnad`): EVS only, the sense EVS illustrates with
a direct question (`docs/curriculum.md`). No other source in the repo has
Russian for question words: the seed has none, PSV, VSL and EKSS have no
Russian, HAR has no question words.

The XML has no root element and undeclared prefixes, one article per line
(`eesti/ekixml.py`). To refresh a file: download, `gzip -9 -n`, replace, run the
matching import with `--check`, commit.

## Reading and listening material

| Source | Licence | Used for |
|---|---|---|
| Selges keeles (WordPress.com API) | no reuse grant — owner-only | reading texts, cloze sentences |
| ERR *Lihtsad uudised* | © ERR — owner-only | weekly reading feed |
| ERR Raadio 4 language archives | © ERR — owner-only | grammar-lesson episodes: audio, transcripts filed as `grammatika` |
| HARNO exam material | © HARNO — owner-only | past tasks and listening audio, downloaded by `cli harvest-exam --download` into `data/exam/` for private study, read in `Eksam`; never committed, never redistributed, always shown with the board's name |
| EIS public tasks | © HARNO — owner-only | the task's own text and its recordings, read in `Eksam` (`cli harvest-exam --download`); scoring stays at EIS, which is the only place the answers exist |
| Own material (`cli ingest`) | treated as ungranted | owner-only |

All owner-only items are served only behind Cloudflare Access.

`cli harvest-reading` keeps existing material if the source returns no readable
posts. EIS and HARNO harvesting are independent: an EIS outage keeps its previous
tasks and still allows HARNO to refresh. Deleting a source also removes its
old topic links. `cli push-content` rebuilds both morphology-derived links and
explicit lesson-label links before uploading the corpus; it requires a built
word list on the publishing machine. `cli link-topics` remains useful for a
local preview. This analysis runs at publication, never in a learner request.

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

| Source | Licence | Used for |
|---|---|---|
| EVKK learner corpus (TLU) | counts only | ranking error tags |
| EstGEC-L2 (TLU) | GPL-3.0, not redistributed | attested word-order corrections |
| GiellaLT `lang-est-x-utee` | LGPL-3.0 — rules re-implemented, nothing copied | agreement exceptions |
| TalTech `inflection_et` | benchmark | validating Vabamorf (`cli validate`) |
| TalTech `grammar_et` | no licence — local only | second eval track (`evals/external.py`) |

## Services

TartuNLP TTS, translation and GEC (public University of Tartu APIs); model
providers in `docs/ai-providers.md`.

## Typeface and icons

| Asset | Licence | Where |
|---|---|---|
| Geologica (Monokrom) | SIL OFL 1.1 | `eesti/web/fonts/`, licence beside the files |
| Phosphor Icons | MIT | inlined in `eesti/web/js/icons.js`; `eesti/web/vendor/phosphor-icons.LICENSE` |

Both are served from this origin; the page asks no font or icon host for anything.
