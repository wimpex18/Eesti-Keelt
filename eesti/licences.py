"""The licence ledger: every third party this project touches, and its terms.

Split out of `eesti/sources.py` on 2026-09-12, where it was 250 of 672 lines
and the larger half of a file whose other job is storing harvested text. The
two have nothing to do with each other at runtime — the store never reads a
`note` and the ledger never opens a database — and everything to do with each
other in review, which is why they were written together and why they should
not stay that way. A session opening `sources.py` to change a query was loading
seventeen licence essays to get to it.

## Why licence and redistributable are columns

Once the app is on a public URL, "may this be served to an anonymous visitor?"
is a question every item must be able to answer, and a flag on the row is the
only way to answer it reliably.

    redistributable = 1  ->  may be served publicly (CC-BY, CC-BY-SA, public API)
    redistributable = 0  ->  owner only, behind auth (HARNO exam material,
                             copyrighted transcripts, anything hand-fed)

HARNO material is the case that forces it. Downloading the official exam PDFs
to study from is ordinary personal use; serving them from a public URL is
redistribution of a state agency's copyrighted work. The same file is fine in
one place and not the other, so access control has to be data-driven — and it
means Cloudflare Access is not a nice-to-have but the thing that keeps this
legitimate.

`changes` is the other obligation, and it is a field for the same reason:
CC BY 4.0 does not ask for a tidy README, it asks that the source be named
**and the changes indicated** wherever the material is presented. `/api/sources`
serves this ledger so the page can do that.

Everything here is re-exported by `eesti.sources`, so `from ..sources import
REGISTRY` keeps working and no call site moved.
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
    #: What this project did to the material, in the words a licence asks for.
    #:
    #: A field rather than a sentence inside `note`, for the same reason
    #: `licence` and `redistributable` are fields: CC BY 4.0 does not ask you to
    #: keep a nice README, it asks you to state the source **and indicate
    #: changes** wherever the material is presented. EKI put it in their own
    #: terms -- process and present it any way needed, provided the reference to
    #: EKI is retained and the modifications are described -- and Ekilex repeats
    #: it. An obligation that has to be *served* cannot live in prose nothing
    #: parses; `/api/sources` renders this one.
    #:
    #: Empty for sources that are only linked to, only counted, or our own.
    changes: str = ""


# The registry. Every source this app is allowed to touch, with the licence that
# governs it. Adding a source means making a licence decision, deliberately.
#: The licence ledger. Two kinds of entry live here, and the difference is worth
#: knowing before reading a "nothing produces this" as a gap:
#:
#: * **Corpus producers** — `err-r4`, `err-lihtsad`, `harno`, `eis`,
#:   `selges-keeles`, `oma-materjal`. A harvester (or `cli ingest`) writes rows
#:   into `items` carrying the id, and `add_items` refuses any id not listed
#:   here. That refusal is the gate.
#: * **Provenance records** — `ekilex-wordlist` (fills `words`), `taltech-gec`
#:   (the attested word-order corrections), `evkk` (an error taxonomy),
#:   `sonapi` and `tartunlp-tts` (live APIs, answers cached not archived),
#:   `ekk` (linked to, with 62 lexical facts stored), `generated` (drills, which
#:   are computed and never stored). Nothing writes `items` for these, and that
#:   is correct: they are here because this project touches them and every
#:   third party it touches has to have its licence written down.
#:
#: `tests/test_sections.py` checks the ledger covers every source id the code
#: writes; it cannot check the second kind, which is why they are named here.
REGISTRY: tuple[Source, ...] = (
    Source(
        "err-r4", "ERR Raadio 4 keeleõppesaated", "harvest",
        "© ERR — personal study only", False,
        "https://r4.err.ee/arhiiv/kak_eto_po_estonski",
        "72 episodes across 3 archives: 28 carrying transcripts, 44 audio "
        "with a blurb. Archives are closed and static, so harvest once and "
        "never re-fetch. **Not ~170** — that figure was extrapolated from the "
        "one series that has transcripts (2010; the 2015 and 2019 series do "
        "not), and it stood in this ledger after README had recorded the "
        "correction, which is what a fact with two homes does.",
    ),
    Source(
        "err-lihtsad", "ERR Lihtsad uudised", "harvest",
        "© ERR — personal study only", False,
        "https://news.err.ee/k/lihtsad-uudised",
        "Simplified Estonian news for learners. Weekly, ongoing — the one live "
        "feed in the app. **Text only.** This note said 'audio + text' until "
        "2026-09-11, when the pages were read: an issue carries no per-issue "
        "audio at all, only ERR's site-wide radio-app banner. `harvest/"
        "lihtsad.py` had it right the whole time — it writes `audio: False` "
        "into every item's meta — so the claim lived in the ledger and "
        "nowhere else, which is the worst place for it: nothing reads a note, "
        "so nothing could contradict it.",
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
        "TalTech pool, not swapped for it: measured 2026-09-12, the two share "
        "not one corrected sentence, and 232 of 237 pass `is_reordering` "
        "unchanged, so one gate still governs both. "
        "`redistributable = 0` is a choice, not a limit — GPL-3.0 permits "
        "conveying the work with its licence and source, and this app conveys "
        "nothing: the corpus rides `content.db` to one deployment behind "
        "Access. MultiGEC-2025 distributes the identical 258 texts as `EIC` "
        "under terms limiting use to scientific and research purposes, which "
        "exam self-study is not; TLU publish it themselves with no such "
        "clause, and that is the door used.",
    ),
    Source(
        "harno", "HARNO tasemeeksami materjalid", "file",
        "© Haridus- ja Noorteamet — personal study only", False,
        "https://harno.ee/eesti-keele-tasemeeksamid",
        "Official sample tasks and listening MP3s for A2/B1/B2/C1. Free to "
        "download and study from; NOT free to republish. Owner-only, always.",
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
        "since 2026-09-13 (4 456 rows). On 2026-09-12 EKI's page asked for an "
        "ID card; direct links worked the next day. Nothing here fetches it. Stored "
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
        "EKI's Estonian–Russian dictionary: 70 882 articles, 60 509 lemmas "
        "with a usable Russian translation (measured 2026-09-13). The Russian "
        "on the word card, the Sõnavara list, drills and review cards, offline — "
        "after the hand-written seed, ahead of Sõnaveeb (`meaning.py`). Imported by `cli import-evs` into the words database as "
        "`evs_gloss` — reference data, like `psv_gloss`, never written into "
        "the learner's `word_gloss`. Same terms as EKI's other downloads: "
        "process and present it any way needed, with the attribution kept "
        "and the changes described.",
        changes="Из словарной статьи взяты заглавное слово, часть речи и не "
                "более пяти русских переводов — по одному на значение, затем "
                "следующие. Отброшены пометы ударения и вида, устаревшие "
                "переводы, формы, управление и переведённые примеры.",
    ),
    Source(
        "eki-har", "Haridussõnastik (EKI)", "file", "CC-BY-4.0", True,
        "https://arhiiv.eki.ee/litsents/",
        "EKI's education terminology: 4 989 articles, 5 871 terms counting "
        "synonyms, with Russian (measured 2026-09-13). The last fallback for "
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
        "with a definition (measured 2026-09-13). Native-level wording, so the "
        "last fallback for a word card's definition, after PSV and Sõnaveeb. "
        "`cli import-vsl`, table `vsl_gloss` in the words database.",
        changes="Взяты заглавное слово и первое определение первой статьи; "
                "этимология, подстатьи, пометы и разметка отброшены.",
    ),
    Source(
        "eki-ekss", "Eesti keele seletav sõnaraamat (EKI)", "file", "CC-BY-4.0", True,
        "https://arhiiv.eki.ee/litsents/",
        "EKI's full explanatory dictionary: 145 882 articles (measured "
        "2026-09-13). Optional — Sõnaveeb already shows these definitions "
        "live, and the image build does not import it. If imported with `cli "
        "import-ekss`, it is consulted after VSL, as the last definition "
        "fallback. Table `ekss_gloss`.",
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
        "learner downloaded, committed gzipped in `deploy/eki/` since "
        "2026-09-13, so the image build imports it. Nothing here fetches it. Stored "
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
        "sonapi", "Sõnaveeb via api.sonapi.ee", "api",
        "Ekilex data CC-BY-4.0; third-party endpoint", True,
        "https://api.sonapi.ee/v2/",
        "Inflection type, rection, Russian glosses, definitions. Single lookups "
        "only — never batch, the upstream asks not to be crawled. Answers are "
        "kept in vocab.db (eesti/gloss.py) so a word is asked about once ever, "
        "capped per day, and the store is private to one learner behind Access "
        "— never redistributed.",
    ),
    Source(
        "tartunlp-tts", "TartuNLP kõnesüntees", "api",
        "University of Tartu public API", True,
        "https://api.tartunlp.ai/text-to-speech/v2",
        "Turns any text into listening practice. 14 voices, 0.7x for learners.",
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
        "ekk", "Eesti keele käsiraamat (EKI)", "file",
        "© Eesti Keele Instituut — linked to, not reproduced", False,
        "https://arhiiv.eki.ee/books/ekk09/index.php",
        "The handbook this project points at instead of restating grammar. Two "
        "uses, both deliberate: every rule explanation links to its section "
        "rather than paraphrasing it, and SÜ 64 — the handbook's own list of "
        "rections people get wrong — is fetched once for 62 lexical facts "
        "(headword, correct frame, marked wrong frame). EKK's example "
        "sentences are **not** stored; rection drills are built over the "
        "harvested corpus instead, so nothing of the prose is reproduced and "
        "the sentences sit at the learner's level rather than the handbook's. "
        "It was the one third party the app uses that this ledger did not "
        "record, found by asking which source ids the code writes.\n\n"
        "EKK 2009 is still the handbook, and this still links to it — but the "
        "norm underneath it moved: **ÕS 2025 became the basis of the written-"
        "language norm on 2026-01-01**, and EKI now route current rection and "
        "usage decisions through the ühendsõnastik in Sõnaveeb (`EKI "
        "selgitab`). That matters here because SÜ 64's 23 contrasts are "
        "asserted *normatively* — the `rektsioon` drill marks an answer wrong "
        "and `rection.errors` corrects free writing — so a contrast ÕS has "
        "since revised would be taught stale. Checked as prose, not as code: "
        "see docs/grammar-scope.md.",
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
        "generated", "Genereeritud harjutused", "generated",
        "own work", True, None,
        "Drills built from Vabamorf forms. Unlimited, deterministic.",
    ),
)
