# Sources

Every third party the app draws on. The ledger of record is
`eesti/licences.py` (`REGISTRY`), served at `/api/sources` and shown in
`Allikad`; `licence` and `redistributable` are columns, so every library item
can answer "may this be shown to anyone but the owner?".

## Language data

| Source | Licence | Used for |
|---|---|---|
| Vabamorf via EstNLTK 1.7.5 | permissive | all forms, analysis, spelling — the answer key |
| Enriched Ekilex word list (KristjanPikhof) | CC-BY-SA-4.0 | 160 000+ lemmas, estimated CEFR, frequency rank |
| EKI *Eesti keele tasemete sõnavara* (`A1A2B1.txt`) | CC-BY-4.0 | official A1/A2/B1 levels, outranks the estimate |
| EKI *põhisõnavara sõnastik* (PSV) | CC-BY-4.0 | learner-level definitions, examples, rection |
| EKI *Eesti-vene sõnaraamat* (EVS) | CC-BY-4.0 | offline Russian, inflection type |
| EKI *Võõrsõnade leksikon* (VSL), *seletav sõnaraamat* (EKSS) | CC-BY-4.0 | fallback Estonian definitions |
| EKI *Haridussõnastik* (HAR) | CC-BY-4.0 | fallback Russian for education terms |
| Ekilex API (EKI) | CC-BY-4.0 | live word card with `EKILEX_API_KEY` |
| Sõnaveeb via `api.sonapi.ee` | Ekilex data CC-BY-4.0, third-party endpoint | live word card without a key |
| *Eesti keele käsiraamat* (EKK) | © EKI — linked, not reproduced | rule links per topic; SÜ 64 rection list |
| `data/seed_glossary.tsv` | own work | 294 hand-written glosses for drill words |

EKI downloads are committed in `deploy/eki/` and imported at image build
(`deploy/eki/README.md`). Keep EKI attribution wherever EKI text is shown.

**Sõnaveeb and Ekilex are never batch-requested**: single lookups, one live
request per second under a lock, each word stored once in `vocab.db`
(`gloss.py`), capped per day. For more than the stored fields, link to
Sõnaveeb (`sonapi.entry_url`).

## Reading and listening material

| Source | Licence | Used for |
|---|---|---|
| Selges keeles (WordPress.com API) | no reuse grant — owner-only | reading texts, cloze sentences |
| ERR *Lihtsad uudised* | © ERR — owner-only | weekly reading feed |
| ERR Raadio 4 language archives | © ERR — owner-only | grammar-lesson episodes; transcripts filed as `grammatika`, example sentences for drills |
| HARNO exam material | © HARNO — owner-only | pointers only; `data/exam/` never committed |
| EIS public tasks | © HARNO — owner-only | pointers only |
| Own material (`cli ingest`) | treated as ungranted | owner-only |

All owner-only items are served only behind Cloudflare Access.

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
