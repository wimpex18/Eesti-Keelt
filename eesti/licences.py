"""The licence ledger: every third party this project touches, and its terms.

    redistributable = 1  ->  may be served publicly (CC-BY, CC-BY-SA, public API)
    redistributable = 0  ->  owner only, behind auth (HARNO material,
                             copyrighted transcripts, anything hand-fed)

Access control is data-driven: nonowner content connections filter sources
before serving items, files or derived exercises.

`changes` is a field because CC BY 4.0 requires naming the source **and
indicating changes** wherever the material is presented; `/api/sources` serves
this ledger to the page.

Re-exported by `eesti.sources` (`from ..sources import REGISTRY`).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Source:
    id: str
    name: str
    kind: str
    licence: str
    redistributable: bool
    url: str | None = None
    note: str = ""
    #: What this project did to the material, as CC BY 4.0 asks ("indicate changes"),
    #: served by `/api/sources`. Empty for sources only linked to, counted, or our own.
    changes: str = ""
    # ------------------------------------------------------------------
    # Engines (`kind="engine"`): what a lane is, and what it costs to use.
    # ------------------------------------------------------------------
    #: The model or dataset version this project pins, where there is one.
    version: str = ""
    #: The lane's own quota or rate limit, in the provider's words.
    quota: str = ""
    #: **What leaves the device**: `none` (runs here), `text`, or `audio`. The
    #: privacy fact a learner is owed before they type or speak into it.
    data_leaves: str = "none"
    #: What the provider says it does with what it receives.
    retention: str = ""
    #: When the terms, the quota and the pinned id were last checked.
    verified: str = ""


# The registry: every source this app may touch, with its licence. Two kinds:
#
# * **Corpus producers** — `err-r4`, `err-lihtsad`, `harno`, `eis`,
#   `selges-keeles`, `oma-materjal`: rows in `items` carry the id, and
#   `add_items` refuses ids not listed here.
# * **Provenance records** — `ekilex-wordlist`, `taltech-gec`, `evkk`, `sonapi`,
#   `tartunlp-tts`, `ekk`, `generated`, the EKI dictionaries: touched by the
#   project but writing no `items` rows.
#
# `tests/test_sections.py` checks the ledger covers every source id the code
# writes.
#: Engines: every model or service the app may call, with what it costs the
#: learner in privacy. A lane missing here is a lane nobody vetted, so
#: `tests/test_engine_registry.py` holds this list against the code.
ENGINES: tuple[Source, ...] = (
    Source(
        "vabamorf", "Vabamorf (via EstNLTK)", "engine",
        "LGPL-2.1 (Vabamorf), GPL-2.0 (EstNLTK)", True,
        "https://github.com/estnltk/estnltk",
        "Morphological analysis and synthesis. Every answer key and every "
        "deterministic check is this: it decides, models do not.",
        data_leaves="none", verified="2026-09-20",
    ),
    Source(
        "tartunlp-gec", "TartuNLP grammar correction", "engine",
        "MIT (API); public backend model licence unverified", True,
        "https://api.tartunlp.ai/grammar",
        "Explicit diagnostic/evaluation only; unavailable public service is excluded "
        "from automatic grammar checks.",
        version="public backend model identity unverified",
        quota="public, unmetered", data_leaves="text",
        retention="TartuNLP store what is sent, to improve the service",
        verified="2026-09-19",
    ),
    Source(
        "tartunlp-mt", "Neurotõlge (TartuNLP translation)", "engine",
        "MIT (the API)", True, "https://api.tartunlp.ai/translation/v2",
        "Sentence translation; est→est normalization is explicit evaluation only.",
        quota="1000 requests per window (x-rate-limit-limit)",
        data_leaves="text",
        retention="TartuNLP store what is sent, to improve the service",
        verified="2026-09-19",
    ),
    Source(
        "workers-ai", "Cloudflare Workers AI", "engine",
        "Cloudflare terms", True,
        "https://developers.cloudflare.com/workers-ai/",
        "Speech recognition on the deployment, and an LLM lane for grammar.",
        version="@cf/openai/whisper-large-v3-turbo, @cf/openai/gpt-oss-120b",
        quota="10 000 neurons/day free, then $0.011/1000",
        data_leaves="audio", retention="not used for training (Cloudflare terms)",
        verified="2026-09-19",
    ),
    Source(
        "anthropic", "Anthropic Claude", "engine", "Anthropic Commercial Terms", True,
        "https://platform.claude.com/docs/",
        "Claude Haiku 5.5 for explanations, tutoring and advisory feedback "
        "(`eesti/providers/claude.py`). An evaluation lane until its grammar "
        "eval passes (ADR-0008); it never decides a drill, mastery or FSRS.",
        version="claude-haiku-5-5",
        quota="paid: $0.10 / $0.50 per million input / output tokens up to a "
              "100K-token prompt; this app caps it at 2 000 calls a day",
        data_leaves="text",
        retention="inputs and outputs deleted within 30 days; not used for "
                  "training by default (Anthropic privacy center, 2026)",
        verified="2026-10-09",
    ),
    Source(
        "nvidia", "NVIDIA NIM", "engine", "NVIDIA developer terms", True,
        "https://build.nvidia.com/", "Evaluation lane; its free endpoint timed out in current probes, excluded from automatic routing.",
        version="deepseek-ai/deepseek-v4.1-flash", quota="40 requests/min",
        data_leaves="text", verified="2026-09-25",
    ),
    Source(
        "mistral", "Mistral AI", "engine", "Mistral terms (Experiment plan)", True,
        "https://mistral.ai/", "Explicit evaluation only; poor grammar detection despite healthy transport.",
        version="mistral-large-latest", quota="organization/model-specific Free mode limits",
        data_leaves="text", verified="2026-09-19",
    ),
    Source(
        "openrouter", "OpenRouter", "engine", "OpenRouter terms", True,
        "https://openrouter.ai/", "Optional free-model evaluation lane; account limits apply.",
        version="dots-studio/dots-3-note-preview:free",
        quota="50 requests/day, failures counted", data_leaves="text",
        verified="2026-09-19",
    ),
    Source(
        "local-llm", "Local LLM (Ollama, EstLLM 8B)", "engine",
        "Llama 3.1 community licence", True, None,
        "The private lane: off unless LOCAL_LLM_URL is set, and then nothing "
        "leaves the machine.",
        version="EstLLM 8B GGUF", quota="your machine", data_leaves="none",
        verified="2026-09-19",
    ),
    Source(
        "hf-whisper", "Hugging Face Inference (Whisper)", "engine",
        "Hugging Face terms", True, "https://huggingface.co/openai/whisper-large-v3",
        "Speech recognition fallback under `cli serve`.",
        version="openai/whisper-large-v3", quota="free tier, rate limited",
        data_leaves="audio", verified="2026-09-19",
    ),
    Source(
        "whisper-cpp", "whisper.cpp with TalTech's Estonian model", "engine",
        "MIT (whisper.cpp and the model)", True,
        "https://huggingface.co/TalTechNLP/whisper-large-v3-turbo-et-verbatim-2604",
        "Local speech recognition: an Estonian benchmark candidate; nothing leaves "
        "the machine. Kept off production pending learner evaluation.",
        version="whisper-large-v3-turbo-et-verbatim-2604", data_leaves="none",
        verified="2026-09-19",
    ),
    Source(
        "inflection-et", "TalTech inflection_et", "engine",
        "Licence not declared — evaluation only", False,
        "https://huggingface.co/datasets/TalTechNLP/inflection_et",
        "Checked against Vabamorf in the morphology eval; not in the request "
        "path or redistributed as learner material. The dataset card does "
        "not declare a licence.",
        data_leaves="none", verified="2026-10-01",
    ),
)


#: EKI's recordings. CC BY 4.0, downloaded once from the archive and imported
#: into `data/audio.db`. The word recordings are played to every learner, with
#: the credit; the sentence corpora stay with the owner, because the novels
#: behind them are still in copyright.
AUDIO: tuple[Source, ...] = (
    Source(
        "psv-haaldused", "Eesti keele põhisõnavara sõnastik 2014 — hääldused",
        "audio", "CC-BY-4.0 (EKI)", True,
        "https://arhiiv.eki.ee/litsents/idkaart/dl.cgi?D=psv%2Fhaaldused",
        "About 6 000 base word forms read by Eva Klemets and Marju Avamere, "
        "indexed by form. The index keeps EKI's quantity and palatalisation "
        "marks, which the spelling does not carry and synthesis guesses. "
        "Played for any word form a learner taps (`/api/pronounce`) and in "
        "unit 1's sound items (`eesti/sounds.py`), whose answer key is EKI's "
        "own form and quantity mark for the recording played.",
        changes="Записи пережаты в 16 кГц моно и обрезаны по краям; оставлены "
                "только те формы слов, которые приложение учит.",
        verified="2026-09-20",
    ),
    Source(
        "eki-konekorpus", "EKI kõnekorpused (Kersti, Külli, Lee, Liivika, Meelis)",
        "audio", "CC-BY-4.0 (EKI); the works read are under their own copyright",
        False,
        "https://arhiiv.eki.ee/litsents/idkaart/dl.cgi?D=konekorpused",
        "Sentences read aloud, each with its text. Dictation plays a person "
        "instead of a synthesiser.",
        changes="Взяты предложения не длиннее 12 слов, пережаты в 16 кГц моно.",
        verified="2026-09-20",
    ),
)


REGISTRY: tuple[Source, ...] = ENGINES + AUDIO + (
    Source(
        "err-r4", "ERR Raadio 4 keeleõppesaated", "harvest",
        "© ERR — personal study only", False,
        "https://r4.err.ee/arhiiv/kak_eto_po_estonski",
        "72 episodes across 3 archives: 28 carrying transcripts, 44 audio "
        "with a blurb (only the 2010 series has transcripts). Archives are "
        "closed and static, so harvest once and never re-fetch.",
    ),
    Source(
        "err-lihtsad", "ERR Lihtsad uudised", "harvest",
        "© ERR — personal study only", False,
        "https://news.err.ee/k/lihtsad-uudised",
        "Simplified Estonian news for learners. Weekly, ongoing — the one live "
        "feed in the app. **Text only**: an issue carries no per-issue audio "
        "(`harvest/lihtsad.py` writes `audio: False`).",
    ),
    Source(
        "taltech-gec", "TalTechNLP grammar_et (both splits) + grammar2_et",
        "file",
        "no licence stated — personal study only", False,
        "https://huggingface.co/datasets/TalTechNLP/grammar_et",
        "9 383 (learner wrote, native corrected) sentence pairs from the "
        "Estonian Native LLM Benchmark family: `grammar_et` test (1 000) and "
        "train (7 937), plus `grammar2_et` (446), which carries the same two "
        "columns. 322 of them are pure re-orderings -- same words, same "
        "punctuation, different sequence -- which "
        "is the only sound source of word-order drills this project has: "
        "correctness is attested rather than inferred. Neither dataset card "
        "states a licence at all, so both are treated as ungranted — same "
        "posture as ERR and HARNO, and never baked into the image.",
    ),
    Source(
        "estgec-l2", "EstGEC-L2 (Tallinna Ülikool)", "file",
        "GPL-3.0", False,
        "https://github.com/tlu-dt-nlp/EstGEC-L2-Corpus",
        "258 texts, 3 721 sentences from the Estonian Interlanguage Corpus — "
        "the same corpus whose error taxonomy weights this curriculum — "
        "error-tagged in M2 format by at least three annotators each, and "
        "published per CEFR level. It supplies word-order items where "
        "`R:WO` is a **label** rather than the inference `wordorder.py` makes "
        "over TalTech's unannotated pairs, and it is the only source of items "
        "here that says what level its writer was sitting at. Merged with the "
        "TalTech pool, not swapped for it: the two share no corrected sentence, "
        "and 232 of 237 pass `is_reordering` unchanged, so one gate governs both. "
        "`redistributable = 0` is a choice, not a limit — GPL-3.0 permits "
        "conveying the work with its licence and source, and this app conveys "
        "nothing: the corpus rides `content.db` to the owner’s authenticated library. MultiGEC-2025 distributes the identical 258 texts as `EIC` "
        "under terms limiting use to scientific and research purposes, which "
        "exam self-study is not; TLU publish it themselves with no such "
        "clause, and that is the door used.",
    ),
    Source(
        "harno", "HARNO tasemeeksami materjalid", "file",
        "© Haridus- ja Noorteamet — personal study only", False,
        "https://harno.ee/eesti-keele-tasemeeksamid",
        "Official sample tasks and listening MP3s for A2/B1/B2/C1. Publicly "
        "available for study; public reuse rights are not established in this "
        "ledger. Currently served only in the owner's library pending source "
        "rights review.",
    ),
    Source(
        "eis", "EIS avalikud ülesanded", "api",
        "© HARNO — personal study only", False,
        "https://eis.harno.ee/publicitems",
        "Official practice tasks, A2-C1 reading and listening, no login needed.",
    ),
    Source(
        "ekilex-wordlist", "Enriched Ekilex wordlist", "file",
        "CC-BY-SA-4.0", True,
        "https://github.com/KristjanPikhof/Estonian-Wordlist-Enriched-Ekilex",
        "CEFR levels and frequency for 160k lemmas.",
        changes="Загружено в словарь приложения, частота пересчитана в ранг. "
                "Там, где официальный список уровней EKI расходится с этим "
                "списком, побеждает EKI, а источник уровня сохраняется "
                "отдельно.",
    ),
    Source(
        "eki-tasemesonavara", "Eesti keele tasemete sõnavara (2018, EKI)", "file",
        "CC-BY-4.0", True,
        "https://arhiiv.eki.ee/litsents/",
        "The exam board's own institute publishing which words are A1, A2 and "
        "B1 — the claim the enriched Ekilex list could only estimate, and it "
        "estimated it for 6.2 % of its lemmas. Imported by `cli import-levels` "
        "from a file the learner downloaded, committed as `deploy/eki/A1A2B1.txt` "
        "(4 456 rows). Nothing here fetches it. Stored "
        "verbatim in `official_levels` and applied to "
        "`words.proficiency` with `words.level_source = 'eki'`. Licence terms "
        "are EKI's own: process and present it any way needed, an app "
        "included, commercial use unrestricted, provided the attribution to "
        "EKI is kept and the changes are described. The changes: rows are "
        "filtered to A1/A2/B1, EKI's one-letter POS codes are mapped onto this "
        "project's tag vocabulary, and the corpus frequency is kept under its "
        "own name rather than written into a column that holds ranks.",
        changes="Оставлены только уровни A1/A2/B1; однобуквенные пометы "
                "частей речи EKI переведены в обозначения этого приложения; "
                "корпусная частота EKI сохранена отдельно и не смешана с "
                "рангом. Формулировки не изменялись.",
    ),
    Source(
        "giellalt-est", "GiellaLT lang-est-x-utee (grammar rules)", "file",
        "LGPL-3.0 — analysis used, no code or data copied", False,
        "https://github.com/giellalt/lang-est-x-utee",
        "Finite-state morphology and Constraint Grammar rules for Estonian, "
        "morphology by Heiki-Jaan Kaalep (Tartu Ülikool). **Nothing of theirs "
        "is copied or shipped.** What is used is the linguistic analysis in "
        "their `&err-agr` rules — which pronoun/verb pairs disagree and, the "
        "valuable half, which apparent disagreements are not errors: `sid` and "
        "`ksid` are 2sg and 3pl alike, and `eks`/`ega` flip a clause to the "
        "imperative. `morph.agreement_errors` reimplements that over "
        "Vabamorf's own tags. Their toolchain is deliberately not adopted: the "
        "CG rules are written against GiellaLT's tagset, so running them means "
        "running a second morphological analyser beside Vabamorf — a second "
        "source of truth for the thing Vabamorf is the answer key for — plus "
        "HFST and VISL CG3 in a free-tier image. Recorded here because this "
        "project touches their work and every third party it touches has its "
        "licence written down.",
    ),
    Source(
        "eki-evs", "Eesti-vene sõnaraamat (EKI)", "file",
        "CC-BY-4.0", True,
        "https://arhiiv.eki.ee/litsents/",
        "EKI's Estonian–Russian dictionary: 70 882 articles, 60 672 lemmas "
        "with a usable Russian translation. The Russian "
        "on the word card, the Sõnavara list, drills and review cards, offline — "
        "after the hand-written seed and the live dictionary (`meaning.py`). Imported by `cli import-evs` into the words database as "
        "`evs_gloss` — reference data, like `psv_gloss`, never written into "
        "the learner's `word_gloss`. The same import stores `evs_question`: "
        "for each küsisõnad answer word, the Russian of the sense EVS "
        "illustrates with a direct question (`kus` → где), shown as the cue "
        "for the drill's blank, and `evs_example`: EVS's example phrases and idioms, "
        "each with EKI's Russian, shown under *Näited* on the word card and "
        "on meaning cards in Järjekord, where one can be built from tiles. "
        "Outside the owner's scope, where the harvested corpus is hidden, the "
        "same phrases are the practice pool (`evs.phrases`): case gap-fill, "
        "the comma drill, word-order tiles, dictation, read-aloud and the "
        "mock's reading and listening sections, each item credited. "
        "Same terms as EKI's other downloads: "
        "process and present it any way needed, with the attribution kept "
        "and the changes described.",
        changes="Из словарной статьи взяты заглавное слово, часть речи и не "
                "более пяти русских переводов — по одному на значение, затем "
                "следующие. Отброшены пометы ударения и вида, устаревшие "
                "переводы, формы и управление. Для "
                "вопросительных слов (küsisõnad) отдельно взяты переводы "
                "того значения, пример к которому — прямой вопрос. Примеры "
                "употребления взяты с русским переводом (не более двух "
                "вариантов), без помет ударения и вида; устаревшие переводы "
                "и специальные термины с пометой области отброшены, "
                "свободное место в примере выделено курсивом. В упражнениях "
                "фразы-примеры используются без изменений, кроме самого "
                "задания: в слове оставлен пропуск, удалена запятая или слова "
                "перемешаны для сборки; знаки препинания при сборке "
                "отброшены.",
    ),
    Source(
        "eki-har", "Haridussõnastik (EKI)", "file", "CC-BY-4.0", True,
        "https://arhiiv.eki.ee/litsents/",
        "EKI's education terminology: 4 989 articles, 5 905 terms counting "
        "synonyms, with Russian. The last fallback for "
        "a word card's Russian, after EVS and Sõnaveeb. `cli import-har`, "
        "table `har_gloss` in the words database.",
        changes="Взяты термины (основной и синонимы) и не более трёх русских "
                "переводов; определения, переводы на другие языки и "
                "редакционные пометы отброшены.",
    ),
    Source(
        "eki-vsl", "Võõrsõnade leksikon (EKI)", "file", "CC-BY-4.0", True,
        "https://arhiiv.eki.ee/litsents/",
        "EKI's lexicon of foreign words: 31 794 articles, 30 095 headwords "
        "with a definition. Native-level wording, so the "
        "last fallback for a word card's definition, after PSV and Sõnaveeb. "
        "`cli import-vsl`, table `vsl_gloss` in the words database.",
        changes="Взяты заглавное слово и первое определение первой статьи; "
                "этимология, подстатьи, пометы и разметка отброшены.",
    ),
    Source(
        "eki-ekss", "Eesti keele seletav sõnaraamat (EKI)", "file", "CC-BY-4.0", True,
        "https://arhiiv.eki.ee/litsents/",
        "EKI's full explanatory dictionary: 145 882 articles, 117 937 lemmas "
        "with a definition, 96 058 of them in the word list. Native-level wording, so the last definition fallback, "
        "after PSV, Sõnaveeb and VSL — the one that still answers offline for "
        "almost every word the learner can click. `cli import-ekss`, table "
        "`ekss_gloss`, committed gzipped and imported by the image build.",
        changes="Взяты заглавное слово и первое определение первой статьи; "
                "примеры, формы, подстатьи и разметка отброшены.",
    ),
    Source(
        "eki-psv", "Eesti keele põhisõnavara sõnastik 2014 (EKI)", "file",
        "CC-BY-4.0", True,
        "https://arhiiv.eki.ee/litsents/",
        "About 6 000 basic words defined in language a learner can read — the "
        "thing *Keeleõppija Sõnaveeb* exists for, published for download "
        "instead of scraped. Imported by `cli import-psv` from a file the "
        "learner downloaded, committed gzipped in `deploy/eki/`, so the "
        "image build imports it. Nothing here fetches it. Stored "
        "in the words database as `psv_gloss`, not in `vocab.db`: it is "
        "reference data, and `vocab.db` travels in the state snapshot, where "
        "a restore replaces the file whole. `/api/enrich` reads it beside "
        "Sõnaveeb's native-level definition and prefers EKI's. "
        "Licence terms are EKI's own: process and present it any way needed, "
        "an app included, commercial use unrestricted, provided the "
        "attribution to EKI is kept and the changes described. The changes: "
        "articles are flattened to headword, first definition and at most "
        "three examples, and of two homonym articles the commoner is kept; "
        "editing metadata and cross-reference markup are dropped. The source "
        "file is redistributed, gzipped, in this public repository, which CC "
        "BY 4.0 permits with this attribution.",
        changes="Из словарной статьи взяты заглавное слово, первое "
                "определение и не более трёх примеров; из статей-омонимов "
                "оставлена более частотная; редакционные пометы и "
                "перекрёстные ссылки отброшены. Сами определения и примеры "
                "показаны так, как их написал EKI.",
    ),
    Source(
        "ekilex", "Ekilex API (EKI)", "api", "CC-BY-4.0", True,
        "https://ekilex.ee/",
        "EKI's own dictionary and term base system — the database Sõnaveeb "
        "shows — through its API with the learner's key (`EKILEX_API_KEY`). "
        "The live dictionary whenever the key is set, ahead of the third-party "
        "`sonapi` mirror: the learner-level definition (`wwLite`), the native "
        "one, the Russian translations of each sense, rection, muuttüüp and "
        "CEFR level. Single lookups, one request a second, each word asked "
        "once and kept in `vocab.db` within `gloss.DAILY_BUDGET`. Terms "
        "(ekilex.ee, 2022): CC BY 4.0, commercial use not restricted, EKI and "
        "Ekilex to be credited and the changes described.",
        changes="Из ответа Ekilex взяты определение для изучающих язык и "
                "полное определение, русские переводы (не более пяти: сначала "
                "основного значения), управление, тип словоизменения и уровень "
                "CEFR; устаревшие значения, переводы родственных значений и "
                "остальные поля отброшены.",
    ),
    Source(
        "sonapi", "Sõnaveeb via api.sonapi.ee", "api",
        "Ekilex data CC-BY-4.0; third-party endpoint", True,
        "https://api.sonapi.ee/v2/",
        "Inflection type, rection, Russian glosses, definitions. Single lookups "
        "only — never batch, the upstream asks not to be crawled. Answers are "
        "kept in vocab.db (eesti/gloss.py) so a word is asked about once ever, "
        "capped per day, and the store is private to its signed-in account "
        "— never redistributed.",
    ),
    Source(
        "tartunlp-tts", "TartuNLP kõnesüntees", "api",
        "University of Tartu public API", True,
        "https://api.tartunlp.ai/text-to-speech/v2",
        "Turns any text into listening practice. 12 Estonian voices, 0.7x for learners.",
    ),
    Source(
        "selges-keeles", "Selges keeles — lihtne eesti keel", "api",
        "© the authors — no explicit reuse licence; personal study only", False,
        "https://selgeskeeles.wordpress.com",
        "349 simplified Estonian news posts, 35-80 words each, 100% Estonian. "
        "Fetched via WordPress.com's public API. Dormant since 2018, which "
        "makes it a fixed corpus — harvest once.",
    ),
    Source(
        "evkk", "EVKK — eesti vahekeele korpus (TLU)", "harvest",
        "taxonomy + counts stored; no explicit reuse licence on the corpus", False,
        "https://evkk.tlu.ee/vers1",
        "51k linguist-annotated errors in learner Estonian. Only the public "
        "error taxonomy and its counts are stored, to weight the curriculum by "
        "what learners actually get wrong. The learner texts are not fetched.",
    ),
    Source(
        "ekk", "Eesti keele käsiraamat 2007 (3rd ed.)", "file",
        "© Mati Erelt, Tiiu Erelt, Kristiina Ross — attributed rules and brief "
        "examples", False,
        "https://arhiiv.eki.ee/books/ekk09/index.php",
        "Own Russian explanations paraphrase the cited rules; brief Estonian "
        "examples are attributed through each lesson's section links. Complete "
        "chapters are not imported. SÜ 65's rection facts (headword, correct "
        "frame, marked wrong frame) are fetched for deterministic practice; "
        "its full example sentences are not imported into that table.\n\n"
        "The handbook is the 2007 third edition, online at EKI's archive. **ÕS "
        "2025 is the basis of the written-language norm from 2026-01-01**; EKI "
        "does not norm rection and records current usage in the ühendsõnastik "
        "(Sõnaveeb). SÜ 65's contrasts whose starred frame EKI now records are "
        "neither drilled nor flagged (`rection.EKI_ACCEPTS`, checked through "
        "Ekilex on 2026-10-08); the rest still mark an answer wrong in the "
        "`rektsioon` drill and in `rection.errors`.",
    ),
    Source(
        "eki-teatmik", "EKI teatmik", "file",
        "© Eesti Keele Instituut — attributed grammatical facts", False,
        "https://teatmik.eki.ee/teatmik/asesonade-kaanamine/",
        "Pronoun forms are transcribed from the named declension tables, with "
        "stress/stem marks removed. Grammar lessons retain the source link. "
        "This record does not grant wholesale reuse of the site's prose.",
    ),
    Source(
        "oma-materjal", "Oma materjal — käsitsi lisatud", "file",
        "unknown, and treated as ungranted — personal study only", False, None,
        "A textbook chapter, a tutor's handout, a transcript typed up by hand: "
        "whatever the learner puts in with `cli ingest`. Not redistributable, "
        "and deliberately not guessed at: this project has no way to know what "
        "licence a file dropped into it carries, and the safe assumption for "
        "somebody else's textbook is the same one it makes about HARNO and "
        "ERR — owner-only, never republished, never baked into the image.",
    ),
    Source(
        "geologica", "Geologica (Monokrom)", "asset", "SIL OFL 1.1", True,
        "https://github.com/googlefonts/geologica",
        "The one typeface of the interface and of Estonian material, served from "
        "this origin (`eesti/web/fonts/`, licence beside the files). Latin, Latin "
        "Extended and Cyrillic subsets, unmodified otherwise.",
    ),
    Source(
        "phosphor", "Phosphor Icons", "asset", "MIT", True,
        "https://github.com/phosphor-icons/core",
        "The interface icons, inlined as paths in `eesti/web/js/icons.js`; the MIT "
        "licence travels in `eesti/web/vendor/phosphor-icons.LICENSE`.",
    ),
    Source(
        "hls-js", "HLS.js", "asset", "Apache-2.0", True,
        "https://github.com/video-dev/hls.js",
        "Unmodified light browser player for ERR HLS recordings; served from "
        "this origin with its upstream licence and notices.",
        version="1.7.3",
    ),
    Source(
        "generated", "Genereeritud harjutused", "generated",
        "own work", True, None,
        "Drills built from Vabamorf forms. Unlimited, deterministic.",
    ),
    Source(
        "eki-valjendid",
        "Kasulikke väljendeid A1-tasemel eesti keele õppijale (EKI)", "file",
        "CC-BY-4.0 (Sõnaveeb terms)", True,
        "https://sonaveeb.ee/learn#v-pills-kasulikke-valjendeid-a1",
        "Sõrmus, Pool, Kallas, Kiisla (2025), EKI: A1 phrases grouped by "
        "communicative function and situation, in Estonian only. Unit 1's "
        "`fraasid` items are built from them (`eesti/phrases.py`), keyed by "
        "EKI's grouping and its two-part exchanges. The page states no licence "
        "of its own; Sõnaveeb's terms put its information under CC BY 4.0.",
        changes="Перенесены фразы разделов 1.1–1.8 и диалоги из 2.3, 2.5, 2.6; "
                "из вариантов через косую черту взят первый (*Mina olen Maria*, "
                "*sularahas*). *Tervist!*, *Tšau!* и *Head ööd!* не "
                "спрашиваются: каждая служит и другой цели. Русский перевод — "
                "из EKI EVS, где он есть.",
        verified="2026-10-09",
    ),
    Source(
        "eki-piltsonastik", "EKI piltsõnastik (Sõnaveeb)", "file",
        "CC-BY-4.0 (Sõnaveeb terms; text only)", True,
        "https://sonaveeb.ee/wordgame",
        "J. Kallas, K. Koppel; illustrations K. Karp, A. Piits-Jamnik; "
        "translations O. Kiisla, E. Dovgan and others. About 1 000 pictured words "
        "in 52 themes, with Russian, Ukrainian, English and German. The unit "
        "spec draws first words from its themes as text; the pictures and the "
        "audio carry no stated licence, so they stay on Sõnaveeb behind a link "
        "until EKI confirms (DEV-55).",
        changes="Взят только выбор слов: из тем *Värvid* и *Toit ja jook* — "
                "слова с пометой A1–A2, для первой недели курса. "
                "Картинки, звук и русские подписи не используются: подпись "
                "называет картинку (*kala* — «окунь»), поэтому перевод — из "
                "словарей EKI. Не взяты *tee* и *või*: у каждого есть омоним.",
        verified="2026-10-09",
    ),
    Source(
        "eki-haaldusharjutused", "EKI e-hääldusharjutused (Sõnaveeb)", "link",
        "not stated", False,
        "https://sonaveeb.ee/pronunciation-exercises/",
        "Six topics, 37 exercises: vowels, diphthongs, stops, palatalisation "
        "and quantity. Unit 1's sound items follow their contrasts and link "
        "here for saying the words aloud; their audio and pictures state no "
        "licence, so none is copied or played (DEV-55 asks EKI).",
        verified="2026-10-09",
    ),
)


#: The credit shown with an item built from a source, as its licence asks.
CREDITS: dict[str, str] = {
    "psv-haaldused": "Salvestis: EKI põhisõnavara sõnastik 2014 · CC BY 4.0",
    "eki-valjendid": ("Sõrmus, Pool, Kallas, Kiisla · Kasulikke väljendeid A1 · "
                      "EKI · CC BY 4.0"),
}


def credit(source_id: str | None) -> str:
    """The attribution an item built from `source_id` carries, or `""`."""
    if not source_id:
        return ""
    from .evs import ATTRIBUTION, SOURCE_ID

    return ATTRIBUTION if source_id == SOURCE_ID else CREDITS.get(source_id, "")
