# Source integrations

The licence ledger is `eesti/licences.py`, exposed through `/api/sources` and
Allikad. `docs/sources.md` gives attribution and permitted transformations.
This map follows the material through its writer, store and learner-facing
reader. Reference data belongs in the image; private study material and
learner state have separate lifecycles.

## Reference and language data

| Upstream | Ingestion and transformation | Storage and learner use | Refresh evidence and limits |
|---|---|---|---|
| Enriched Ekilex word list, GitHub | `eesti/cli/build.py` fetches the commit and SHA-256 pinned in `eesti/reference.py`; `eesti/wordlist.py` reads lemma, frequency rank, estimated level and part of speech | `data/eesti.db` words; vocabulary, placement, drill selection and reading coverage. `eesti/export.py` builds `data/edge.db` using round-trip-checked Vabamorf forms | Checksum rejects unexpected or partial downloads before replacement. Empty/malformed imports preserve words and derived forms. Estimates are identified separately from EKI levels; coverage is not CEFR |
| EKI A1/A2/B1 vocabulary | Licensed `deploy/eki/A1A2B1.txt`; `cli import-levels` collapses duplicate lemmas to the lowest official level | `official_levels` and `words.level_source`; official levels outrank estimates | Image records the input hash and imported count. The authenticated upstream has no automatically verified newest-byte comparison |
| EKI PSV, EVS, HAR, VSL and EKSS | Licensed XML in `deploy/eki/`; `eesti/ekixml.py` reads article fragments; respective importers keep definitions, translations, examples and grammatical data | Reference tables in `data/eesti.db`; word cards, Russian cues, phrase practice, offline fallbacks | File hashes identify the image inputs; row counts establish whether each optional import landed. EKI's download process requires registration/ID-card access for these dictionaries |
| Ekilex API | `eesti/providers/ekilex.py`; authenticated single lookups, one per second; senses, learner/native definitions, Russian translations, rection and usage examples | `eesti/gloss.py` stores answers in the learner's `vocab.db`; `eesti/meaning.py` and word-card API read them | Daily budget and permanent cached answers protect the upstream. Cached entries, including misses, have no automatic expiry; a live result does not date every saved word |
| Sõnaveeb mirror | `eesti/providers/sonapi.py` uses v2 when no Ekilex key is configured | Same word-card/gloss path; private JSON cache and learner database | Third-party endpoint, single lookups only. It is not the official API and must not be batch-crawled |
| Vabamorf / EstNLTK | Analysis, synthesis and round-trip checks in `eesti/morph.py`, `eesti/forms.py` and generators | Deterministic drill and review keys; contextual word readings | Runtime distribution version is reported by health. An upgrade requires the morphology evaluation; model explanations never replace these keys |
| EKI handbook, Teatmik and PSV grammar tables | Source-backed Russian points in `eesti/lessontext.py`, links in `eesti/grammar.py`, tables in `eesti/lessons.py`; pronouns transcribed from Teatmik in `eesti/pronouns.py` | Reegel → deterministic practice → feedback; links retain authority and attribution | Archived handbook rules are not dated by HTTP success. Norm-sensitive claims require comparison with current EKI guidance; no automatic wholesale rule rewriting |
| EKK SÜ 65 rection facts | `cli rections`, `eesti/rection.py` | Reference table; rection drills and deterministic writing evidence | Optional build fetch may fail on datacenter IPs; health reports actual count. Current rection norms require EKI's current usage guidance |
| Own glossary and generated items | `data/seed_glossary.tsv`; deterministic generators and signed item references | Russian seed meanings and unlimited Estonian drills; learner evidence/FSRS in separate stores | Seed is curated, not a live dictionary; generated sentences and model proposals carry their own attribution/boundaries |

## Reading, listening, speaking and exams

| Upstream | Ingestion and transformation | Store → in-app reader | Coverage and limits |
|---|---|---|---|
| Selges keeles WordPress archive | `eesti/harvest/selges.py`; v1.1 API pages, advertised-total validation, markup cleaning and relative difficulty | `data/content.db` items → Lugemine, cloze and topic links | Closed archive, 349 readable posts; publication ends in 2018. This is reading practice, not current news or an official CEFR corpus |
| ERR Lihtsad uudised | `eesti/harvest/lihtsad.py`; live feed and article prose | Same private corpus → Lugemine and comprehension questions | Manual harvest; no scheduled news refresh. Parser currently supplies text without a listening recording |
| ERR Raadio 4 archives | `eesti/harvest/err.py`; three seed series, cached page graph, episode text and media URLs | Same private corpus → Saated with section pagination; `eesti/web/js/media.js` plays MP3/HLS inside the app | Reachable archive pages define the crawl, not a promised full historical catalogue. HTML cache has no expiry; audio streams remain dependent on ERR |
| EKI PSV pronunciation | `cli import-haaldused`, `eesti/haaldus.py`; licensed local archive | `data/audio.db` → GCS read-only mount → word-form playback for every learner and unit 1's sound items (`eesti/sounds.py`); TTS fallback for word forms only | Presence is reported as recording counts; without them the sound topic says so and resume passes it. Licensing of each speech corpus still matters; pronunciation scoring is not provided |
| EKI Sõnaveeb learner pages (*Kasulikke väljendeid A1*, piltsõnastik, e-hääldusharjutused) | Transcribed as text in code: phrases in `eesti/phrases.py`, the first week's word selection in `eesti/units.py` | Unit 1's phrase items and first words; the exercises are linked | Sõnaveeb's terms put its information under CC BY 4.0; the pictures and exercise audio state no licence and are not copied (DEV-55) |
| EKI read-speech corpora | `cli import-konekorpus`; selected licensed sentence recordings | Same audio store → human-voiced dictation | Selected recording coverage is not the whole upstream corpus; audio and underlying read works have distinct rights |
| TartuNLP TTS and translation | Public v2 APIs, `eesti/providers/tts.py` and `eesti/providers/translate.py`; documented request/response formats | Cached WAV/MP3 synthesis and advisory translations; text playback, dictation and conversation voice | Service availability and model identity are separate from configuration. Machine translation is not an authoritative lexical source |
| Home speech service and Workers AI Whisper | Worker routes audio to `deploy/home-asr/` through the existing VPC binding; Whisper fallback | Tentative transcript stays editable in the app; ordinary practice audio is unsaved | Recogniser engine is named. Quality needs human-verified learner audio; current evidence is below the pilot floor (`docs/asr-evaluation.md`) |
| HARNO proficiency-exam page | `eesti/harvest/harno.py` classifies level panels, purpose, PDF/audio/video; validated atomic downloads and explicit re-fetch | Private `data/exam/` → GCS read-only mount; catalogue in content DB → Eksam native PDF pages, figures, media and reviewed controls | A2/B1 are the target. Other levels are indexed only on request. Forms/statistics are deliberately excluded from learning sections. PDFs are not graded until printed keys and extraction are reviewed |
| HARNO formats and sittings | `eesti/exam.py`; official published formats, timings, registration windows | Eksam, timer, readiness and learner-selected calendar export | B1 writing: 35 minutes for two tasks; A2 writing: 30. B1 listening remains 30–35. A sitting is learner state. Unpublished future sittings remain unknown; no date is inferred |
| EIS public items | `eesti/harvest/eis.py`; cookie/rid catalogue, per-level search, task iframe and recordings | Private task text/audio → Eksam; official scoring stays at EIS | Server-held keys are not copied or invented. A search requests 200 rows per level; additional pagination would need implementation if that ceiling were reached |
| HARNO introduction videos | HARNO catalogue carries official YouTube identifiers | Existing video player inside the app | Embedded third-party player can fail independently; there is no unverified transcript or model-produced answer key |
| Hand-added material | `cli ingest` and `eesti/sources.py` | Private content store, existing library modes | Licence is unknown and treated as ungranted; no automatic public redistribution |

Corpus refreshes merge by source URL and level, retain issued ids and usable
content, and record catalogue check time and content/file hashes. Failed
responses do not establish freshness. Topic links are rebuilt at publication.
The owner's Durable Object archives shared corpus; guests/permanent learners
restore it before use while retaining separate progress. HARNO files and EKI
recordings travel via GCS mounts, not the corpus snapshot. Publishing either
without the other can leave catalogue entries whose downloads are absent.
Owner health confirms the origin and archived corpus checksums, including a
replacement uploaded during the same boot. Atomic chunk-generation publication
retains the earlier archive if a replacement fails; older archives remain
readable. The procedure is in `docs/deploy.md`.

## Engines, evaluation and implementation assets

| Source/tool | Role | Availability boundary |
|---|---|---|
| Workers AI GPT-OSS-120B | Automatic hosted tutor/grammar lane | Followed by deterministic offline evidence; changing the lane requires its own evaluation |
| TartuNLP public GEC, NVIDIA, Mistral, OpenRouter, local EstLLM | Explicit grammar evaluation/diagnostics | Excluded from automatic routing. Aliases and public backend identities may be unversioned; reachability alone is not qualification |
| Hugging Face Whisper, whisper.cpp, local speech candidates | Local/evaluation speech options | Production home/fallback chain remains unchanged; published model revision is not proof of installed weights |
| TalTech inflection benchmark, TalTech grammar dataset | Morphology and grammar evaluation | `eesti/evals/morphology.py`, `eesti/evals/external.py`; no learner material redistribution |
| EstGEC-L2, GiellaLT | Attested word-order corrections and analysed agreement exceptions | GPL/LGPL boundaries in the licence ledger; GiellaLT code/data are not shipped |
| EVKK taxonomy | Error-frequency weighting | Cached taxonomy/counts only; learner essays are not fetched. Legacy taxonomy is not the full current corpus |
| Python, FastAPI, Uvicorn, FSRS | Origin and review runtime | `requirements.txt` requests latest stable; `requirements.lock` fixes what is installed, refreshed by upgrade PRs; health reports installed versions |
| pypdf, PDFium, pdfplumber, Pillow | In-app official PDF extraction/rendering | Row/file presence alone does not establish visual readability or a reviewed key |
| Wrangler, Workers types, TypeScript, axe-core, pytest, Playwright | Worker build, contracts and browser checks | Lockfile/test runtime identify installed versions; build tools are not services served to learners |
| HLS.js | Native browser playback of ERR HLS | Pinned vendored light build; upstream Apache licence/notices accompany it |
| Geologica, Phosphor | Locally served font and icons | OFL/MIT notices remain alongside assets |

## Learning gaps and candidate sources

The current production explanations and word meanings are Russian, with
Estonian labels and examples. English/Ukrainian speakers can use Estonian
material but do not have equivalent instructional support. The course's first
unit, *Algus*, is a stage, not a CEFR level (`docs/course-structure.md`).
Five topics remain reference-only; open speaking is practice evidence, not an
acoustic score or exam result. See `docs/status.md` for the current boundaries.

The product brief in `PRODUCT.md` confirms Russian for the MVP, English and
Ukrainian next, a complete beginner path, and onboarding through a chosen start
or an assessment. Shared lesson and progress identities must survive a change
of explanation language. Linear DEV-40 tracks the course, DEV-42 the explanation
languages.

Keeleklikk/Keeletee are the state's free courses for beginner/A2/B1 with
multilingual guidance; each Grove unit links to its companion unit's public
course map (`eesti/units.py`), but free access is not permission to rehost their
animations, video and exercises. EKI's English dictionary download is marked
public domain; its reversed Estonian-English file explicitly warns about use
and needs a sense/quality review before adopting it as learner translations.
EKI's Estonian-Ukrainian resources are relevant but their exact reusable export
and licence need confirmation. These candidates belong in the durable backlog
until quality and rights support an integration; links alone would not fill the
in-app learning gap.
