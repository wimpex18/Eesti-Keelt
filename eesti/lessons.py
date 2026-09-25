"""The Reegel page: one topic's rule, its forms, examples and the learner's own
mistakes, in one place.

Nothing here is a hand-typed form. Tables come from Vabamorf's synthesiser for a
few sample words; examples are the topic's own drill items with the answer
filled in, which code has already checked; mistakes are the learner's missed
attempts from the evidence log. The prose is the EKK summary
(`grammar.REFERENCES`) and, where a topic needs more, `eesti/lessontext.py`.
"""

from __future__ import annotations

import sqlite3

from .morph import synthesize

#: Case names as the exam and EKK use them, with Vabamorf's tag stem.
CASES = (
    ("nimetav", "n"), ("omastav", "g"), ("osastav", "p"),
    ("sisseütlev", "ill"), ("seesütlev", "in"), ("seestütlev", "el"),
    ("alaleütlev", "all"), ("alalütlev", "ad"), ("alaltütlev", "abl"),
    ("saav", "tr"), ("rajav", "ter"), ("olev", "es"),
    ("ilmaütlev", "ab"), ("kaasaütlev", "kom"),
)
_CASE = dict(CASES)

#: What each case answers and its ending, singular and plural, as EKI's
#: learner grammar tables give them (*Eesti keele grammatika tabelid*, PSV).
CASE_INFO = {
    "nimetav": ("kes? mis?", "Ø", "d"),
    "omastav": ("kelle? mille?", "Ø", "te, de, e"),
    "osastav": ("keda? mida?", "t, Ø, d, tt", "id, sid, e/i/u"),
    "sisseütlev": ("kellesse? millesse? kuhu?", "sse; lühike: Ø, de, tte",
                   "tesse, desse, esse"),
    "seesütlev": ("kelles? milles? kus?", "s", "tes, des, es"),
    "seestütlev": ("kellest? millest? kust?", "st", "test, dest, est"),
    "alaleütlev": ("kellele? millele? kuhu?", "le", "tele, dele, ele"),
    "alalütlev": ("kellel? millel? kus?", "l", "tel, del, el"),
    "alaltütlev": ("kellelt? millelt? kust?", "lt", "telt, delt, elt"),
    "saav": ("kelleks? milleks?", "ks", "teks, deks, eks"),
    "rajav": ("kelleni? milleni?", "ni", "teni, deni, eni"),
    "olev": ("kellena? millena?", "na", "tena, dena, ena"),
    "ilmaütlev": ("kelleta? milleta?", "ta", "teta, deta, eta"),
    "kaasaütlev": ("kellega? millega?", "ga", "tega, dega, ega"),
}
CASE_SOURCE = "https://arhiiv.eki.ee/dict/psv/grammatikatabelid.pdf"

#: Sample words for tables. Choosing them states no fact; their forms come
#: from Vabamorf. `sõber` and `tuba` show gradation, `maja` a vowel stem; the
#: verbs are the ones EKI's learner grammar tables conjugate.
NOUNS = ("raamat", "maja", "tuba", "sõber")
VERBS = ("lubama", "laulma", "tulema")

PERSONS = ("ma", "sa", "ta", "me", "te", "nad")

#: Which cases each noun topic shows, and in which numbers.
NOUN_TABLES: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "pohivormid": (("nimetav", "omastav", "osastav"), ("sg", "pl")),
    "gen-stem": (("nimetav", "omastav", "seesütlev", "kaasaütlev"), ("sg",)),
    "astmevaheldus": (("nimetav", "omastav", "osastav", "seesütlev"), ("sg",)),
    "osastav": (("nimetav", "osastav"), ("sg", "pl")),
    "mitmus": (tuple(c for c, _ in CASES), ("pl",)),
    "kohakaanded": (("sisseütlev", "seesütlev", "seestütlev",
                     "alaleütlev", "alalütlev", "alaltütlev"), ("sg",)),
    "harvad-kaanded": (("saav", "rajav", "olev", "ilmaütlev", "kaasaütlev"), ("sg",)),
    "obj-case": (("nimetav", "omastav", "osastav"), ("sg", "pl")),
}

#: Verb topics: row label and Vabamorf tag, or a (auxiliary, tag) pair for
#: forms built with `olema`/`ei`.
VERB_TABLES: dict[str, tuple[tuple[str, str], ...]] = {
    "olevik": tuple(zip(PERSONS, ("n", "d", "b", "me", "te", "vad"))),
    "lihtminevik": tuple(zip(PERSONS, ("sin", "sid", "s", "sime", "site", "sid"))),
    "verb-form": (("ma-tegevusnimi", "ma"), ("da-tegevusnimi", "da"),
                  ("olevik, ma", "n"), ("lihtminevik, ta", "s"),
                  ("nud-kesksõna", "nud"), ("tud-kesksõna", "tud")),
    "ma-da-inf": (("ma-tegevusnimi", "ma"), ("da-tegevusnimi", "da")),
    "ma-vormid": (("ma", "ma"), ("mas", "mas"), ("mast", "mast"), ("mata", "mata"),
                  ("maks", "maks"), ("des-vorm", "des")),
    "kaskiv": (("sina", "o"), ("tema", "gu"), ("meie", "gem"), ("teie", "ge"),
               ("nemad", "gu")),
    "tingiv": tuple(zip(PERSONS, ("ksin", "ksid", "ks", "ksime", "ksite", "ksid"))),
    "kesksonad": (("v-kesksõna", "v"), ("nud-kesksõna", "nud"),
                  ("tav-kesksõna", "tav"), ("tud-kesksõna", "tud")),
    "umbisikuline": (("olevik", "takse"), ("lihtminevik", "ti"),
                     ("tud-kesksõna", "tud")),
    "kaudne": (),
}

def _with(word: str, tag: str):
    """A row that puts a fixed word before one synthesised form: `ei tee`, `ära tee`."""
    def make(verb: str) -> str:
        form = _forms(verb, tag).split(" ~ ")[0]
        return f"{word} {form}".strip() if form else ""
    return make


def _neg_present(verb: str) -> str:
    from .forms import connegative

    found = connegative(verb)
    return f"ei {found}" if found else ""


#: Rows built from parts, as EKI's tables build them: negation with `ei`, the
#: negative imperative with `ära/ärgu/ärgem/ärge`, the past conditional and the
#: past of the indirect mood with `oleks(in)`/`olevat` + nud.
EXTRA_ROWS = {
    "olevik": (("eitav", _neg_present),),
    "kaskiv": (("eitav: sina", _with("ära", "o")), ("eitav: tema", _with("ärgu", "gu")),
               ("eitav: meie", _with("ärgem", "gem")), ("eitav: teie", _with("ärge", "ge"))),
    "tingiv": (("minevik: ma", _with("oleksin", "nud")), ("minevik: ta", _with("oleks", "nud")),
               ("eitav", _with("ei", "ks"))),
    "umbisikuline": (("eitav olevik", _with("ei", "ta")),
                     ("tingiv", _with("", "taks"))),
    "kaudne": (("olevik", _with("", "vat")), ("minevik", _with("olevat", "nud")),
               ("eitav", _with("ei", "vat")), ("umbisikuline", _with("", "tavat"))),
}

#: Tenses built with an auxiliary: the auxiliary's tag per person, then the
#: main verb's participle.
COMPOUND_TABLES: dict[str, tuple[str, tuple[str, ...], str]] = {
    "taisminevik": ("olema", ("n", "d", "b", "me", "te", "vad"), "nud"),
    "enneminevik": ("olema", ("sin", "sid", "s", "sime", "site", "sid"), "nud"),
}


def _forms(lemma: str, tag: str) -> str:
    try:
        found = list(dict.fromkeys(synthesize(lemma, tag) or []))
    except Exception:  # noqa: BLE001 - an unknown form is a blank cell, not an error
        found = []
    return " ~ ".join(found)


def _case(lemma: str, number: str, case: str) -> str:
    """One case form; the singular illative also gets its short form (`tuppa`)."""
    full = _forms(lemma, f"{number} {_CASE[case]}")
    if (number, case) == ("sg", "sisseütlev"):
        short = _forms(lemma, "adt")
        # A short illative spelled like the partitive (`sõpra`) is left out: the
        # synthesiser offers it for many words, and nothing here says it is used.
        if short and short not in full.split(" ~ ") and short != _forms(lemma, f"{number} p"):
            return f"{short} ~ {full}" if full else short
    return full


def table(topic: str, words: sqlite3.Connection | None = None) -> dict | None:
    """A form table for the topic, every cell from Vabamorf, or None."""
    if topic == "asesonad":
        from .pronouns import table as pronoun_table

        return pronoun_table()
    if topic == "vordlusastmed" and words is not None:
        from .patterns import comparatives

        pairs = comparatives(words, limit=60)[:6]
        return {"columns": ["algvõrre", "keskvõrre", "ülivõrre"],
                "rows": [[p, c, f"kõige {c}"] for p, c, _ in pairs]} if pairs else None
    if topic in NOUN_TABLES:
        cases, numbers = NOUN_TABLES[topic]
        rows = []
        for number in numbers:
            for case in cases:
                label = case if len(numbers) == 1 else f"{case} · {'ainsus' if number == 'sg' else 'mitmus'}"
                question, sg, pl = CASE_INFO[case]
                rows.append([label, question, sg if number == "sg" else pl,
                             *(_case(w, number, case) for w in NOUNS)])
        return {"columns": ["", "küsimus", "tunnus", *NOUNS], "rows": rows}
    if topic in VERB_TABLES:
        rows = [[label, *(_forms(v, tag) for v in VERBS)]
                for label, tag in VERB_TABLES[topic]]
        for label, make in EXTRA_ROWS.get(topic, ()):
            rows.append([label, *(make(v) for v in VERBS)])
        return {"columns": ["", *VERBS], "rows": rows}
    if topic in COMPOUND_TABLES:
        aux, tags, participle = COMPOUND_TABLES[topic]
        rows = [[person, *(f"{_forms(aux, tag)} {_forms(v, participle)}" for v in VERBS)]
                for person, tag in zip(PERSONS, tags)]
        return {"columns": ["", *VERBS], "rows": rows}
    if topic == "eitus":
        from .forms import connegative, past_participle

        return {"columns": ["", *VERBS], "rows": [
            ["olevik", *(f"ei {connegative(v) or ''}" for v in VERBS)],
            ["lihtminevik", *(f"ei {past_participle(v) or ''}" for v in VERBS)],
        ]}
    if topic in ("arvsonad", "jargarvud"):
        from .patterns import ORDINALS

        if topic == "arvsonad":
            return {"columns": ["nimetav", "omastav", "osastav"],
                    "rows": [[n, _forms(n, "sg g"), _forms(n, "sg p")]
                             for n, _ in ORDINALS]}
        return {"columns": ["põhiarv", "järgarv", "omastav"],
                "rows": [[n, o, _forms(o, "sg g")] for n, o in ORDINALS]}
    return None


def examples(topic: str, count: int = 5, seed: int = 0) -> list[dict]:
    """The topic's own drill sentences with the answer in place, shortest first."""
    from .item import BLANK
    from .practice import items_for

    try:
        items = items_for(topic, count=count * 3, seed=seed)
    except Exception:  # noqa: BLE001 - a topic with no generator has no examples
        return []
    out = []
    for it in items:
        prompt, answer = getattr(it, "prompt", ""), getattr(it, "answer", "")
        if prompt and answer and prompt.count(BLANK) == 1:
            before, after = prompt.split(BLANK)
            if not any(e["before"] == before for e in out):
                out.append({"before": before, "answer": answer, "after": after})
    out.sort(key=lambda e: len(e["before"]) + len(e["after"]))
    return out[:count]


def mistakes(log: sqlite3.Connection, topic: str, limit: int = 5) -> list[dict]:
    """The learner's latest missed attempts in this topic, one per sentence."""
    rows = log.execute(
        "SELECT payload FROM events WHERE type = 'attempt'"
        " AND json_extract(payload, '$.topic') = ?"
        " AND json_extract(payload, '$.correct') = 0 ORDER BY seq DESC LIMIT 60",
        (topic,),
    ).fetchall()
    import json

    out, seen = [], set()
    for (raw,) in rows:
        p = json.loads(raw)
        if p.get("prompt") in seen:
            continue
        seen.add(p.get("prompt"))
        out.append({"prompt": p.get("prompt", ""), "given": p.get("answer", ""),
                    "expected": p.get("expected", "")})
        if len(out) == limit:
            break
    return out


def _rule(ref) -> dict | None:
    if ref is None:
        return None
    return {"et_term": ref.et_term, "ru_term": ref.ru_term, "summary_ru": ref.summary_ru,
            "ekk_section": ref.ekk_section, "url": ref.url}


def lesson(topic: str, *, log: sqlite3.Connection | None = None,
           content: sqlite3.Connection | None = None,
           words: sqlite3.Connection | None = None) -> dict | None:
    """Everything the Reegel page shows for one topic, or None for an unknown id."""
    from .curriculum import TOPICS
    from .lessontext import LESSONS, TIPS

    t = next((x for x in TOPICS if x.id == topic), None)
    if t is None:
        return None
    text = LESSONS.get(topic)
    related = []
    if content is not None:
        from .topiclinks import related as linked

        try:
            related = linked(content, topic, limit=3)
        except sqlite3.Error:
            related = []
    return {
        "id": t.id, "level": t.level, "et": t.et, "ru": t.ru,
        "drillable": bool(t.generator),
        "rule": _rule(t.reference),
        "tip": ({"gist_ru": TIPS[topic].gist_ru, "wrong": TIPS[topic].wrong,
                 "right": TIPS[topic].right} if topic in TIPS else None),
        "points_ru": list(text.points_ru) if text else [],
        "sources": [{"label": s.label, "url": s.url} for s in text.sources] if text else [],
        "table": table(topic, words),
        "examples": examples(topic) if t.generator else [],
        "mistakes": mistakes(log, topic) if log is not None else [],
        "reading": related,
    }
