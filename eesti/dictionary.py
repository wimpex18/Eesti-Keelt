"""Sõnastik: the learner's dictionary. One entry per lemma, found by any form.

An entry is assembled from sources; nothing in it is written here, and every
part names who said it:

  part of speech       the word list (`words`), else EKI EVS
  level                EKI's A1/A2/B1 list (`official_levels`), else an
                       identified estimate: Ekilex's sense level from the
                       stored live answer, then the enriched Ekilex word list
  forms                Vabamorf: synthesised and read back as this lemma in
                       this form (`_readback`); pronouns from the EKI
                       teatmik's tables, since Vabamorf declines them wrongly
  recordings           EKI's PSV recordings (`audio.db`), exact form and tag
  meanings  ru         `meaning.russian`: seed, stored live answer, EVS, HAR
            en, uk     the stored live answer (Ekilex or the Sõnaveeb mirror:
                       EKI's combined dictionary, sense by sense); where no
                       source has one, a gloss a model drafted, kept only when
                       a second model's blind back-translation named this word
                       again (`model_gloss`), shown as the model's
  definition, rection  EKI PSV, else EKI VSL or EKSS
  examples, idioms     EKI EVS, with EKI's Russian

Everything here reads local tables. The live dictionary is asked by the card's
second request (`/api/enrich`), exactly as before, so an entry never waits on
a third party; what the live dictionary stored for a word is read back here.

The model-drafted glosses are reference content, not learner data: kept in
`content/dictionary/glosses.jsonl` with their evidence and imported into the
words database at image build (`import_glosses`). The pipeline that drafts and
checks them is `eesti/dictionary_glosses.py`.
"""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

from . import evs, meaning
from .lookup import POS_NAMES, TAG_NAMES, TAG_RU

#: The forms a learner needs, as EKI's learner dictionaries give them: a
#: noun's singular and plural nimetav, omastav, osastav; a verb's two
#: infinitives, the third person of the present and the past, both
#: participles and the impersonal present.
NOUN_TAGS = ("sg n", "sg g", "sg p", "pl n", "pl g", "pl p")
VERB_TAGS = ("ma", "da", "b", "s", "nud", "tud", "takse")

#: The fourteen cases in EKI's order, for the full table (`paradigm`).
CASES = ("n", "g", "p", "ill", "in", "el", "all", "ad", "abl", "tr", "ter", "es", "ab", "kom")

#: The word list's part-of-speech codes as Vabamorf writes them. Synthesis is
#: asked for the entry's own part of speech: *viis* is *viie* as a numeral and
#: *viisi* as a noun.
VABAMORF_POS = {"s": "S", "adj": "A", "num": "N", "pron": "P", "v": "V", "prop": "H"}

#: Parts of speech whose forms Vabamorf is asked for. Pronouns are not: their
#: tables come from the EKI teatmik (`pronouns.TABLES`).
DECLINED = frozenset({"s", "adj", "num", "prop"})

#: EKI's one-letter codes in the level list (`official_levels.pos`), named.
EKI_POS_NAMES = {
    "S": "nimisõna", "A": "omadussõna", "V": "tegusõna", "D": "määrsõna",
    "P": "asesõna", "N": "arvsõna", "O": "arvsõna", "J": "sidesõna",
    "K": "kaassõna", "I": "hüüdsõna", "G": "omadussõna", "Y": "lühend",
}

#: The word list writes some parts of speech two ways.
_POS_ALIASES = {"conj": "konj"}

#: The source id model-drafted glosses carry; it is never a dictionary's.
MODEL_SOURCE = "klint-glosses"

#: How many results a search returns.
SEARCH_LIMIT = 20

#: The longest query read. A dictionary headword is short; a sentence is not.
MAX_QUERY = 60

#: Separator inside a stored list, as `gloss.py` and `evs.py` use it.
SEP = "\x1f"


# ---------------------------------------------------------------------------
# Parts of speech and level
# ---------------------------------------------------------------------------

def _pos_codes(pos: str | None) -> list[str]:
    """The word list's comma-joined codes (`adj,s`), aliases folded."""
    out = []
    for code in (pos or "").replace(" ", "").split(","):
        code = _POS_ALIASES.get(code, code)
        if code and code not in out:
            out.append(code)
    return out


def _pos_block(codes: list[str]) -> dict:
    named = [POS_NAMES[c] for c in codes if c in POS_NAMES]
    return {"codes": codes,
            "names": [et for et, _ in named],
            "ru": [ru for _, ru in named]}


def _word_row(words: sqlite3.Connection, lemma: str) -> sqlite3.Row | None:
    try:
        cur = words.execute(
            "SELECT word, freq_rank, proficiency, pos, level_source FROM words WHERE word = ?",
            (lemma,))
    except sqlite3.Error:
        return None
    row = cur.fetchone()
    if row is None:
        return None
    return dict(zip((d[0] for d in cur.description), row))


def _official(words: sqlite3.Connection, lemma: str) -> list[tuple[str, str]]:
    """EKI's list's lines for a word, `(level, EKI part of speech)`, lowest level
    first: one per part of speech it lists (`official_level_pos`), else the one
    row `official_levels` keeps."""
    for query in ("SELECT level, pos FROM official_level_pos WHERE word = ? ORDER BY level",
                  "SELECT level, pos FROM official_levels WHERE word = ?"):
        try:
            rows = words.execute(query, (lemma,)).fetchall()
        except sqlite3.Error:
            continue
        if rows:
            return [(r[0], r[1] or "") for r in rows]
    return []


def level(words: sqlite3.Connection, lemma: str, codes: list[str],
          live_level: str | None = None) -> dict | None:
    """The word's level and who says so.

    EKI's own list first. It names a part of speech per row, which is not always
    the entry's: *mina* is listed as the noun ("ego") at B1, while the pronoun is
    listed as *ma* — so the row's part of speech is returned, and `same_word`
    says whether it is the entry's. Without the list, an estimate, named as one:
    Ekilex's level for the word's main sense (the stored live answer), then the
    enriched Ekilex word list. A level is CEFR vocabulary only, never a claim
    about the learner (`AGENTS.md`).
    """
    from .wordlist import EKI_POS

    def same(eki_pos: str) -> bool:
        code = EKI_POS.get(eki_pos, "")
        return not codes or not code or _POS_ALIASES.get(code, code) in codes

    listed = _official(words, lemma)
    if listed:
        lvl, eki_pos = next((row for row in listed if same(row[1])), listed[0])
        return {"level": lvl, "source": "eki-tasemesonavara", "estimate": False,
                "listed_as": EKI_POS_NAMES.get(eki_pos), "same_word": same(eki_pos)}
    if live_level:
        return {"level": live_level, "source": "ekilex", "estimate": True,
                "listed_as": None, "same_word": True}
    row = _word_row(words, lemma)
    if row and row["proficiency"] and row["level_source"] != "eki":
        return {"level": row["proficiency"], "source": "ekilex-wordlist", "estimate": True,
                "listed_as": None, "same_word": True}
    return None


# ---------------------------------------------------------------------------
# Forms
# ---------------------------------------------------------------------------

def _readback(lemma: str, tag: str, pos: str = "", hint: str = "") -> list[str]:
    """Every form Vabamorf synthesises for `lemma` in `tag` that reads back as
    this lemma in this form, in Vabamorf's order. Two survivors are parallel
    forms (*maju* ~ *majasid*), shown as EKI shows them; the answer keys of the
    drills use `morph.unique_form`, which refuses them."""
    from estnltk.vabamorf.morf import synthesize

    from .morph import _readings

    out = []
    try:
        produced = synthesize(lemma, tag, pos, hint=hint) or []
    except Exception:  # noqa: BLE001 - a word Vabamorf cannot inflect has no forms
        return []
    for form in dict.fromkeys(produced):
        if any(l.casefold() == lemma.casefold() and f == tag for l, f in _readings(form)):
            out.append(form)
    return out


def _attested(words: sqlite3.Connection, lemma: str) -> set[str]:
    """The word forms EKI's own text uses for this lemma: EVS's phrases and
    idioms, PSV's examples. Lower-case tokens."""
    text: list[str] = []
    try:
        text += [r[0] for r in words.execute(
            "SELECT estonian FROM evs_example WHERE lemma = ?", (lemma,))]
    except sqlite3.Error:
        pass
    try:
        row = words.execute("SELECT examples FROM psv_gloss WHERE lemma = ?", (lemma,)).fetchone()
        if row and row[0]:
            text.append(row[0].replace(SEP, " "))
    except sqlite3.Error:
        pass
    return {t.casefold() for t in re.findall(r"[^\W\d_]+", " ".join(text))}


def _hint(words: sqlite3.Connection, lemma: str, pos: str) -> str:
    """The singular genitive that names the paradigm, or `""`.

    Vabamorf keeps some lemmas with two paradigms: *kool* reads as *kooli* and as
    *koola*, *reis* as *reisi* (a journey) and *reie* (a thigh). Synthesis
    given the genitive keeps to one. The genitive is the one Vabamorf reads back,
    or, where it reads back two, the one EKI's own phrases for the word use;
    when EKI uses both or neither, no paradigm is chosen and both are shown.
    """
    genitives = _readback(lemma, "sg g", pos)
    if len(genitives) == 1:
        return genitives[0]
    used = [g for g in genitives if g.casefold() in _attested(words, lemma)]
    return used[0] if len(used) == 1 else ""


#: Vabamorf's short illative, which the lookup's names leave out: EKI's
#: *lühike sisseütlev* (*majja*), glossed as the illative is (`lookup.TAG_RU`).
EXTRA_NAMES = {"adt": ("lühike sisseütlev", "ед. ч., краткий иллатив (куда)")}


def tag_name(tag: str) -> tuple[str, str]:
    """A Vabamorf tag's Estonian name and its Russian gloss."""
    if tag in EXTRA_NAMES:
        return EXTRA_NAMES[tag]
    return TAG_NAMES.get(tag, tag), TAG_RU.get(tag, "")


def _tag_row(tag: str, forms: list[str]) -> dict:
    name, ru = tag_name(tag)
    return {"tag": tag, "name": name, "ru": ru, "forms": forms}


#: The short illative is EKI's *lühike sisseütlev*: Vabamorf tags it `adt` and
#: it is shown first in the illative's row, as EKI's dictionaries list it.
SHORT_ILLATIVE = "adt"


def forms(words: sqlite3.Connection, lemma: str, codes: list[str]) -> dict:
    """What the entry shows of the word's forms, and whose they are.

    `rows` are the forms a learner needs (`NOUN_TAGS`, `VERB_TAGS`); `paradigm`
    is every case in both numbers, for the full table. A tag with no form that
    reads back is left out rather than guessed. Words that do not inflect have
    neither, and say so with `kind`.
    """
    from .pronouns import CASES as PRONOUN_CASES, TABLES

    if lemma in TABLES:
        number, cells = TABLES[lemma]
        prefix = "sg" if number == "ainsus" else "pl"
        by_case = dict(zip(PRONOUN_CASES, cells))
        tags = dict(zip(PRONOUN_CASES, CASES))
        table = [_tag_row(f"{prefix} {tags[c]}", by_case[c].split(" ~ ")) for c in PRONOUN_CASES]
        return {"kind": "pronoun", "source": "eki-teatmik", "rows": table[:3],
                "paradigm": table, "number": number}
    if "v" in codes:
        rows = [_tag_row(tag, found) for tag in VERB_TAGS
                if (found := _readback(lemma, tag, "V"))]
        return {"kind": "verb", "source": "vabamorf", "rows": rows, "paradigm": []} if rows \
            else {"kind": None, "source": None, "rows": [], "paradigm": []}
    declined = next((c for c in codes if c in DECLINED), None)
    if declined is None:
        return {"kind": "pronoun" if "pron" in codes else None, "source": None,
                "rows": [], "paradigm": []}
    pos = VABAMORF_POS[declined]
    hint = _hint(words, lemma, pos)
    paradigm = []
    for number in ("sg", "pl"):
        for case in CASES:
            tag = f"{number} {case}"
            found = _readback(lemma, tag, pos, hint)
            if case == "ill" and number == "sg":
                short = _readback(lemma, SHORT_ILLATIVE, pos, hint)
                found = list(dict.fromkeys(short + found))
            if found:
                paradigm.append(_tag_row(tag, found))
    if not any(r["tag"] == "sg g" for r in paradigm):
        return {"kind": None, "source": None, "rows": [], "paradigm": []}
    rows = [r for tag in NOUN_TAGS for r in paradigm if r["tag"] == tag]
    return {"kind": "noun", "source": "vabamorf", "rows": rows, "paradigm": paradigm,
            "variants": not hint}


# ---------------------------------------------------------------------------
# Recordings
# ---------------------------------------------------------------------------

def _audio(path: str | Path | None = None) -> sqlite3.Connection | None:
    """EKI's recordings, read-only; None where they are not mounted."""
    from . import config

    target = Path(path or config.AUDIO_DB)
    if not target.exists():
        return None
    try:
        conn = sqlite3.connect(f"file:{target}?mode=ro", uri=True)
        conn.execute("SELECT 1 FROM pronunciation LIMIT 1")
        return conn
    except sqlite3.Error:
        return None


def recordings(lemma: str, rows: list[dict], audio: sqlite3.Connection | None) -> dict | None:
    """Marks each form EKI recorded (exactly that form in exactly that tag) and
    returns the headword's own recording, or None.

    A recording read for one tag is never offered for another spelt alike: EKI
    reads *kassi* twice, the genitive and the partitive, with different length.
    """
    if audio is None:
        return None
    spelt = sorted({f for row in rows for f in row["forms"]} | {lemma})
    try:
        found = {(r[0], r[1]) for r in audio.execute(
            f"SELECT form, tag FROM pronunciation WHERE form IN ({','.join('?' * len(spelt))})",
            spelt)}
        whole = audio.execute(
            "SELECT form FROM pronunciation WHERE tag = '' AND lemma = ? LIMIT 1",
            (lemma,)).fetchone()
    except sqlite3.Error:
        return None
    for row in rows:
        row["recorded"] = [f for f in row["forms"] if (f, row["tag"]) in found]
    head_tag = next((r["tag"] for r in rows[:1]), "")
    if (lemma, head_tag) in found and head_tag:
        return {"form": lemma, "tag": head_tag}
    if whole:
        return {"form": whole[0], "tag": ""}
    return None


# ---------------------------------------------------------------------------
# Meanings
# ---------------------------------------------------------------------------

MODEL_SCHEMA = """
-- Glosses a model drafted where no source has an English or Ukrainian
-- translation, each kept only after a second model's blind back-translation
-- named the word again. Reference content, imported at image build from
-- `content/dictionary/glosses.jsonl`; never shown as a source's.
CREATE TABLE IF NOT EXISTS model_gloss (
    lemma        TEXT NOT NULL,
    lang         TEXT NOT NULL,      -- en | uk
    gloss        TEXT NOT NULL,      -- \x1f-joined, main sense first
    engine       TEXT NOT NULL,      -- the drafting model
    prompt       TEXT NOT NULL,      -- its prompt version
    checker      TEXT NOT NULL,      -- the back-translating model
    check_prompt TEXT NOT NULL,
    back         TEXT NOT NULL,      -- the checker's Estonian, \x1f-joined
    anchor       TEXT NOT NULL,      -- EKI's Russian the draft was asked from
    PRIMARY KEY (lemma, lang)
) WITHOUT ROWID;
"""

#: The languages a gloss is drafted in. Russian always has EKI's.
GLOSS_LANGS = ("en", "uk")


def model_glosses(words: sqlite3.Connection, lemma: str) -> dict[str, dict]:
    """`{lang: gloss}` for one lemma; `{}` without the table."""
    try:
        rows = words.execute(
            "SELECT lang, gloss, engine, prompt, checker, check_prompt, back FROM model_gloss"
            " WHERE lemma = ?", (lemma,)).fetchall()
    except sqlite3.Error:
        return {}
    return {r[0]: {"words": [w for w in r[1].split(SEP) if w], "engine": r[2],
                   "prompt": r[3], "checker": r[4], "check_prompt": r[5],
                   "back": [w for w in r[6].split(SEP) if w]} for r in rows}


def meanings(words: sqlite3.Connection, store: sqlite3.Connection | None, lemma: str) -> dict:
    """Russian, English and Ukrainian, each with whose it is.

    A source always wins: a stored live answer's English or Ukrainian (EKI's
    combined dictionary) is shown and the model's draft is not. A model's draft
    is only ever under `model`, never under `source`.
    """
    from . import gloss as gloss_store

    stored = None
    if store is not None:
        try:
            stored = gloss_store.stored(store, lemma)
        except sqlite3.Error:
            stored = None
    live = stored if stored is not None and stored.found else None
    russian, ru_source = meaning.russian(
        words, lemma, live.russian if live else (),
        live_source=live.source if live else "sonapi")
    out = {"ru": {"words": list(russian), "source": ru_source} if russian else None}
    drafted = model_glosses(words, lemma)
    for lang, field in (("en", "english"), ("uk", "ukrainian")):
        sourced = tuple(getattr(live, field, None) or ()) if live else ()
        if sourced:
            out[lang] = {"words": list(sourced[:meaning.SHOWN]), "source": live.source}
        elif lang in drafted:
            out[lang] = {"words": drafted[lang]["words"][:meaning.SHOWN], "source": None,
                         "model": {k: v for k, v in drafted[lang].items() if k != "words"}}
        else:
            out[lang] = None
    return out


# ---------------------------------------------------------------------------
# Definition, rection, examples
# ---------------------------------------------------------------------------

def definition(words: sqlite3.Connection, lemma: str) -> dict | None:
    """EKI's learner-level definition (PSV), else a native-level one (VSL,
    EKSS), with its examples and rection where PSV has them."""
    from .ekidefs import lookup as native
    from .psv import lookup as psv

    simple = psv(words, lemma)
    if simple and simple.definition:
        return {"text": simple.definition, "source": "eki-psv",
                "examples": list(simple.examples), "rection": list(simple.rection)}
    other = native(words, lemma)
    if other:
        source, text = other
        return {"text": text, "source": source, "examples": [],
                "rection": list(simple.rection) if simple else []}
    if simple and (simple.examples or simple.rection):
        return {"text": None, "source": "eki-psv", "examples": list(simple.examples),
                "rection": list(simple.rection)}
    return None


# ---------------------------------------------------------------------------
# The learner's own relation to the word
# ---------------------------------------------------------------------------

def _status(store: sqlite3.Connection | None, lemma: str) -> str | None:
    from .vocab import STATUS_NAMES, statuses

    if store is None:
        return None
    try:
        return STATUS_NAMES.get(statuses(store, [lemma]).get(lemma, 0))
    except sqlite3.Error:
        return None


def _in_review(review: sqlite3.Connection | None, lemma: str) -> bool:
    if review is None:
        return False
    try:
        return review.execute(
            "SELECT COUNT(*) FROM review_items WHERE lemma = ?", (lemma,)).fetchone()[0] > 0
    except sqlite3.Error:
        return False


# ---------------------------------------------------------------------------
# Sources
# ---------------------------------------------------------------------------

#: Sources that are files of this project rather than entries of the ledger.
OWN = {"seed": ("Klint: käsitsi kirjutatud tõlked (data/seed_glossary.tsv)", "own work")}


def _named(source_id: str, what: str) -> dict:
    from .licences import REGISTRY

    found = next((s for s in REGISTRY if s.id == source_id), None)
    name, licence = (found.name, found.licence) if found else OWN.get(source_id, (source_id, ""))
    return {"id": source_id, "what": what, "name": name, "licence": licence}


def _sources(parts: dict) -> list[dict]:
    """Every source the entry shows something from, once, with what it gave."""
    out: list[dict] = []

    def add(source_id: str | None, what: str) -> None:
        if not source_id:
            return
        for s in out:
            if s["id"] == source_id:
                if what not in s["what"].split(", "):
                    s["what"] += ", " + what
                return
        out.append(_named(source_id, what))

    add(parts["forms"]["source"], "vormid")
    if parts["level"]:
        add(parts["level"]["source"], "tase")
    for lang in ("ru", "en", "uk"):
        m = parts["meanings"][lang]
        if m and m.get("source"):
            add(m["source"], "tõlge")
    if any(parts["meanings"][l] and parts["meanings"][l].get("model") for l in GLOSS_LANGS):
        add(MODEL_SOURCE, "mudeli koostatud tõlge")
        add("anthropic", "mudel")
    if parts["recording"] or any(r.get("recorded") for r in parts["forms"]["rows"]):
        add("psv-haaldused", "hääldus")
    if parts["definition"]:
        add(parts["definition"]["source"], "seletus")
    if parts["examples"] or parts["idioms"]:
        add(evs.SOURCE_ID, "näited")
    return out


# ---------------------------------------------------------------------------
# The entry
# ---------------------------------------------------------------------------

def _evs_pos(words: sqlite3.Connection, lemma: str) -> str | None:
    try:
        row = words.execute("SELECT pos FROM evs_gloss WHERE lemma = ?", (lemma,)).fetchone()
    except sqlite3.Error:
        return None
    return row[0] if row and row[0] else None


def entry(words: sqlite3.Connection, lemma: str, *, store: sqlite3.Connection | None = None,
          review: sqlite3.Connection | None = None,
          audio: sqlite3.Connection | None = None) -> dict | None:
    """The whole entry for one lemma, or None when no source knows the word."""
    lemma = (lemma or "").strip()
    if not lemma:
        return None
    row = _word_row(words, lemma)
    codes = _pos_codes(row["pos"] if row else None) or _pos_codes(_evs_pos(words, lemma))
    from . import gloss as gloss_store

    live = None
    if store is not None:
        try:
            live = gloss_store.stored(store, lemma)
        except sqlite3.Error:
            live = None
    parts = {
        "forms": forms(words, lemma, codes),
        "level": level(words, lemma, codes, getattr(live, "level", None) if live else None),
        "meanings": meanings(words, store, lemma),
        "definition": definition(words, lemma),
        "examples": evs.examples(words, lemma),
        "idioms": evs.examples(words, lemma, evs.IDIOM),
    }
    parts["recording"] = recordings(lemma, parts["forms"]["rows"], audio)
    known = (row is not None or any(parts["meanings"].values()) or parts["definition"]
             or parts["examples"] or parts["forms"]["rows"])
    if not known:
        return None
    return {
        "lemma": lemma,
        "pos": _pos_block(codes),
        **parts,
        "status": _status(store, lemma),
        "in_review": _in_review(review, lemma),
        "sources": _sources(parts),
    }


# ---------------------------------------------------------------------------
# Search: any form, a beginning, or a Russian word
# ---------------------------------------------------------------------------

_CYRILLIC = re.compile(r"[Ѐ-ӿ]")
_QUERY = re.compile(r"[^\w' -]+")


def clean(query: str) -> str:
    """The query as searched: letters, spaces, hyphens; lower case; short."""
    text = _QUERY.sub(" ", (query or "")[:MAX_QUERY])
    return " ".join(text.split()).casefold()


def _form_matches(form: str) -> list[tuple[str, list[str]]]:
    """(lemma, tags) for a surface form: the exported form index first
    (`edge.db`), else Vabamorf itself, for words past the index's 25 000."""
    from .lookup import lookup

    found = lookup(form)
    if found.get("found"):
        return [(a["lemma"], [t["tag"] for t in a["tags"]]) for a in found["analyses"]]
    from .morph import _readings

    out: dict[str, list[str]] = {}
    # A name is capitalised (*Tallinnas*); the query was folded to lower case.
    for spelt in dict.fromkeys((form, form[:1].upper() + form[1:])):
        try:
            for lemma, tag in sorted(_readings(spelt)):
                if lemma:
                    out.setdefault(lemma, []).append(tag)
        except Exception:  # noqa: BLE001 - without Vabamorf the index is all there is
            return []
        if out:
            break
    return [(lemma, [t for t in tags if t]) for lemma, tags in out.items()]


def _known(words: sqlite3.Connection, lemmas: list[str]) -> set[str]:
    """Which of `lemmas` a dictionary here describes: a word-list row with a part
    of speech, an EKI level or an EVS article. Vabamorf reads forms of words no
    dictionary lists, and the word list keeps untagged rows that are forms
    filed as headwords (*kooli*)."""
    if not lemmas:
        return set()
    marks = ",".join("?" * len(lemmas))
    out: set[str] = set()
    for query in (f"SELECT word FROM words WHERE word IN ({marks}) AND pos IS NOT NULL AND pos != ''",
                  f"SELECT word FROM official_levels WHERE word IN ({marks})",
                  f"SELECT lemma FROM evs_gloss WHERE lemma IN ({marks})"):
        try:
            out |= {r[0] for r in words.execute(query, lemmas)}
        except sqlite3.Error:
            continue
    return out


def _rank(words: sqlite3.Connection, lemma: str) -> tuple:
    """Levelled words first, then the commoner."""
    row = _word_row(words, lemma) or {}
    rank = row.get("freq_rank") or 10 ** 9
    return (not row.get("proficiency"), rank, lemma)


def _prefixed(words: sqlite3.Connection, prefix: str, limit: int) -> list[str]:
    """Words that begin with `prefix`, the levelled and the common first."""
    try:
        found = [r[0] for r in words.execute(
            "SELECT word FROM words WHERE word >= ? AND word < ? AND word NOT LIKE '% %'"
            " AND pos IS NOT NULL AND pos != ''"
            " ORDER BY (proficiency IS NULL), (freq_rank IS NULL OR freq_rank = 0), freq_rank,"
            " length(word) LIMIT ?", (prefix, prefix + "\uffff", limit))]
    except sqlite3.Error:
        return []
    return found


def _by_russian(words: sqlite3.Connection, query: str, limit: int) -> list[str]:
    """Lemmas EVS translates with exactly this Russian word, commonest first."""
    sep = SEP
    escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    try:
        rows = words.execute(
            "SELECT e.lemma FROM evs_gloss e LEFT JOIN words w ON w.word = e.lemma"
            " WHERE lower(e.russian) = ? OR lower(e.russian) LIKE ? ESCAPE '\\'"
            " OR lower(e.russian) LIKE ? ESCAPE '\\' OR lower(e.russian) LIKE ? ESCAPE '\\'"
            " ORDER BY (w.proficiency IS NULL), (w.freq_rank IS NULL OR w.freq_rank = 0),"
            " w.freq_rank LIMIT ?",
            (query, f"{escaped}{sep}%", f"%{sep}{escaped}", f"%{sep}{escaped}{sep}%",
             limit)).fetchall()
    except sqlite3.Error:
        return []
    return [r[0] for r in rows]


def _row(words: sqlite3.Connection, lemma: str, glosses: dict, match: dict | None) -> dict:
    row = _word_row(words, lemma)
    codes = _pos_codes(row["pos"] if row else None) or _pos_codes(_evs_pos(words, lemma))
    lvl = level(words, lemma, codes)
    return {"lemma": lemma, "pos": _pos_block(codes),
            "level": lvl["level"] if lvl and lvl["same_word"] else None,
            "russian": glosses.get(lemma, [])[:meaning.SHOWN], "match": match}


def search(words: sqlite3.Connection, query: str, *, store: sqlite3.Connection | None = None,
           limit: int = SEARCH_LIMIT) -> dict:
    """Entries for a query: the lemmas of a form (*majja* → *maja*), lemmas that
    begin with it, or, for a Russian word, the lemmas EVS translates with it.

    `match` on a result names the form the query was and what Vabamorf says it
    is, so the page can show it at the word. Nothing found: Vabamorf's spelling
    suggestions, never a guessed word.
    """
    q = clean(query)
    out = {"query": q, "results": [], "suggestions": [], "russian": bool(_CYRILLIC.search(q))}
    if not q:
        return out
    limit = max(1, min(limit, 50))
    seen: dict[str, dict | None] = {}
    if out["russian"]:
        for lemma in _by_russian(words, q, limit):
            seen.setdefault(lemma, None)
    else:
        # The words the query is a form of, the query itself among them when a
        # dictionary lists it (*mulle* is a rare noun, and *mina* in the
        # allative): levelled and common first. Then the words it begins.
        found: dict[str, dict | None] = {}
        if _known(words, [q]):
            found[q] = None
        for lemma, tags in _form_matches(q):
            if lemma in found or not _known(words, [lemma]):
                continue
            found[lemma] = {"form": q, "tags": [
                {"tag": t, "name": tag_name(t)[0], "ru": tag_name(t)[1]} for t in tags]}
        for lemma in sorted(found, key=lambda l: _rank(words, l)):
            seen[lemma] = found[lemma]
        for lemma in _prefixed(words, q, limit):
            seen.setdefault(lemma, None)
    lemmas = list(seen)[:limit]
    glosses = meaning.russian_many(words, store, lemmas)
    out["results"] = [_row(words, lemma, glosses, seen[lemma]) for lemma in lemmas]
    if not out["results"] and not out["russian"]:
        from .morph import misspellings

        try:
            found = misspellings(q)
        except Exception:  # noqa: BLE001 - a suggestion is a courtesy
            found = []
        out["suggestions"] = [s for m in found for s in m.get("suggestions", [])][:5]
    return out


# ---------------------------------------------------------------------------
# Model-drafted glosses: stored with their evidence, re-checked on import
# ---------------------------------------------------------------------------

#: The checked glosses, in the repository; the image imports them.
GLOSSES = Path(__file__).resolve().parent.parent / "content" / "dictionary" / "glosses.jsonl"

_LATIN = re.compile(r"^[A-Za-z][A-Za-z '’().,/-]*$")
#: Ukrainian's alphabet and apostrophe; Russian's own letters are refused, so a
#: Russian word passed off as Ukrainian does not pass.
_UKRAINIAN = re.compile(r"^[А-ЩЬЮЯЄІЇҐа-щьюяєіїґ][А-ЩЬЮЯЄІЇҐа-щьюяєіїґ 'ʼ’().,/-]*$")
RUSSIAN_ONLY = set("ыэъёЫЭЪЁ")

#: At most this many equivalents, each at most this long.
MAX_EQUIVALENTS = 3
MAX_LENGTH = 40


def _word_problem(lang: str, word: str) -> str | None:
    """Why one equivalent may not be shown, or None."""
    if len(word) > MAX_LENGTH:
        return f"too long: {word[:20]}…"
    if lang == "en" and not _LATIN.match(word):
        return f"not English letters: {word}"
    if lang == "uk":
        if set(word) & RUSSIAN_ONLY:
            return f"Russian letters: {word}"
        if not _UKRAINIAN.match(word):
            return f"not Ukrainian letters: {word}"
    return None


def gate(lang: str, equivalents: list) -> tuple[list[str], str | None]:
    """The equivalents a draft may keep, or why it may keep none.

    Code checks what code can: the script (English Latin, Ukrainian in its own
    alphabet without Russian's letters ы, э, ъ, ё), the count and the length. A
    word Ukrainian shares with Russian (*зуб*, *сад*) is Ukrainian and stays.
    The first equivalent is the main sense: when it fails, the whole draft is
    refused, so a secondary sense never stands alone as the word's meaning; a
    later one that fails is dropped. Whether the meaning is right is the
    back-translation's question (`agrees`).
    """
    if not isinstance(equivalents, list):
        return [], "not a list"
    kept: list[str] = []
    for n, raw in enumerate(equivalents):
        if not isinstance(raw, str):
            return [], "not text"
        word = " ".join(raw.split())
        problem = _word_problem(lang, word) if word else "empty main sense"
        if problem and n == 0:
            return [], problem
        if problem or not word:
            continue
        if word.casefold() not in {k.casefold() for k in kept}:
            kept.append(word)
    if not kept:
        return [], "empty"
    if len(kept) > MAX_EQUIVALENTS:
        return [], f"{len(kept)} equivalents"
    return kept, None


def main_sense_kept(gloss: list[str], draft: list[str], flagged: list[str] = ()) -> str | None:
    """Why a kept gloss has lost its main sense, or None: its first word must be
    the draft's first, and no word the checker flagged may remain."""
    if draft and (not gloss or gloss[0] != draft[0]):
        return f"main sense dropped: {draft[0]}"
    left = {w.casefold() for w in flagged or ()} & {w.casefold() for w in gloss}
    return f"flagged word kept: {', '.join(sorted(left))}" if left else None


def agrees(lemma: str, back: list[str]) -> bool:
    """Whether a blind back-translation names `lemma` again: one of the
    checker's Estonian candidates is the lemma, or a form Vabamorf reads as it
    (*ma* is a form of *mina*). Decided by code, never by a model."""
    from .morph import _readings

    want = lemma.casefold()
    for candidate in back or ():
        if not isinstance(candidate, str):
            continue
        said = " ".join(candidate.split()).casefold()
        if said == want:
            return True
        try:
            if any(l.casefold() == want for l, _ in _readings(said) if l):
                return True
        except Exception:  # noqa: BLE001 - an unreadable candidate is no agreement
            continue
    return False


def check_record(record: dict) -> str | None:
    """Why a stored gloss record may not be shown, or None. The import runs this
    on every line, so a hand edit to the file cannot slip past the gates."""
    for key in ("lemma", "lang", "gloss", "engine", "prompt", "checker", "check_prompt", "back"):
        if not record.get(key):
            return f"missing {key}"
    if record["lang"] not in GLOSS_LANGS:
        return f"unknown language {record['lang']!r}"
    if record["engine"] == record["checker"]:
        return "the checker must be a different model"
    kept, why = gate(record["lang"], list(record["gloss"]))
    if why:
        return why
    if kept != list(record["gloss"]):
        return "gloss not in its gated form"
    if "draft" in record:
        draft, _ = gate(record["lang"], list(record["draft"]))
        lost = main_sense_kept(kept, draft, record.get("flagged") or ())
        if lost:
            return lost
    if not agrees(record["lemma"], list(record["back"])):
        return "the back-translation does not name the word"
    return None


def import_glosses(words: sqlite3.Connection, path: Path | str | None = None) -> dict[str, int]:
    """Replace `model_gloss` with the checked file's records that pass
    `check_record`. Idempotent; a missing file empties the table."""
    target = Path(path or GLOSSES)
    words.executescript(MODEL_SCHEMA)
    rows, refused = [], 0
    if target.exists():
        for line in target.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                refused += 1
                continue
            if check_record(record):
                refused += 1
                continue
            rows.append((record["lemma"], record["lang"], SEP.join(record["gloss"]),
                         record["engine"], record["prompt"], record["checker"],
                         record["check_prompt"], SEP.join(record["back"]),
                         SEP.join(record.get("anchor") or ())))
    with words:
        words.execute("DELETE FROM model_gloss")
        words.executemany(
            "INSERT OR REPLACE INTO model_gloss (lemma, lang, gloss, engine, prompt, checker,"
            " check_prompt, back, anchor) VALUES (?,?,?,?,?,?,?,?,?)", rows)
    return {"stored": len(rows), "refused": refused}
