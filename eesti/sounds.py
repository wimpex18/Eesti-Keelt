"""`tahestik`: hear the difference a sound makes, in EKI's own recordings.

The recordings are EKI's *Eesti keele põhisõnavara sõnastik 2014* (CC BY 4.0),
read by native speakers and indexed with EKI's marks (`eesti/haaldus.py`): a
backquote before a third-quantity syllable (*s`alli*), which the spelling does
not show. The contrasts follow EKI's *e-hääldusharjutused* on Sõnaveeb, which
the rule page links to for saying them aloud; their own audio states no licence,
so it is not played here.

Three rules, each keyed by what EKI recorded, never by a synthesiser's guess:

- **valde** — II against III quantity in one spelling: *selle salli* (omastav,
  no mark) or *seda salli* (osastav, marked). EKK O 8: the genitive and
  partitive of many nouns differ only by quantity.
- **taht** — one vowel letter: *kapp*/*käpp*, *koht*/*kõht*.
- **pikkus** — a short against a long sound: *kana*/*kanna*. A doubled *k, p,
  t, s, f, š* is left out: between vowels a single one is already long, so
  *kapi*/*kappi* is II against III quantity (EKK O 8), not short against long.

Compounds (EKI writes a `+` at the seam) wait for a later unit, and a pair is
drawn from words the word list puts at A1–A2 where there are any (`_everyday`).
A server without the recordings says so rather than playing synthesis for a
quantity contrast.
"""

from __future__ import annotations

import random
import sqlite3
from functools import lru_cache
from pathlib import Path

from .item import BLANK
from .patterns import PatternDrill

SOURCE_ID = "psv-haaldused"
EXERCISES_URL = "https://sonaveeb.ee/pronunciation-exercises/"

BASE_RULES = ("valde", "taht", "pikkus")

#: Vowel letters a learner from Russian hears as one (EKI's exercises: a–ä, ö–õ,
#: u–õ–ö–Ü, i–ü, e–ö).
_VOWELS = (frozenset("aä"), frozenset("oõö"), frozenset("uü"), frozenset("eö"),
           frozenset("iü"))

#: Short enough for a first week, and one plain word.
_LONGEST = 7

#: Letters whose doubling marks quantity, not a short against a long sound.
_QUANTITY_LETTERS = frozenset("kptsfš")

_WHY = {
    "valde": ("**Välde** (долгота): *selle salli* (omastav) — II долгота, *seda "
              "salli* (osastav) — III, более долгий первый слог. Пишутся одинаково, "
              "различаются только произношением (EKK O 8)."),
    "taht": ("*õ, ä, ö, ü* — отдельные звуки, а не варианты *o, a, u*: от одной "
             "буквы меняется слово."),
    "pikkus": ("Краткий и долгий звук различают слова: *kana* — *kanna*. "
               "Долгий звук пишется двумя буквами."),
}


def _recorded_pairs() -> dict[str, list[tuple]]:
    """This server's pairs, read once per version of the recordings file: in
    production it is a network mount, and every sound set would scan it."""
    from . import config

    # Opening creates a file, so look first: no recordings is a state to report.
    path = Path(config.AUDIO_DB)
    if not path.exists():
        raise ValueError("EKI's recordings are not on this server — no sound items")
    stat = path.stat()
    pairs = _pairs_of(str(path.resolve()), stat.st_mtime_ns, stat.st_size)
    if not any(pairs.values()):
        raise ValueError("EKI's recordings are not on this server — no sound items")
    return pairs


@lru_cache(maxsize=2)
def _pairs_of(path: str, mtime: int, size: int) -> dict[str, list[tuple]]:
    from . import haaldus

    conn = haaldus.connect(path)
    try:
        rows = conn.execute(
            "SELECT form, tag, spoken FROM pronunciation WHERE source = ?",
            (SOURCE_ID,)).fetchall()
    finally:
        conn.close()
    return _pairs([r for r in rows if "+" not in r["spoken"] and " " not in r["form"]
                   and "-" not in r["form"] and len(r["form"]) <= _LONGEST])


def _pairs(rows) -> dict[str, list[tuple]]:
    """`rule -> [(played_form, played_tag, answer, other)]` over what EKI recorded."""
    out: dict[str, list[tuple]] = {r: [] for r in BASE_RULES}
    by_form: dict[str, dict[str, str]] = {}
    for r in rows:
        by_form.setdefault(r["form"].casefold(), {})[r["tag"]] = r["spoken"]

    for form, tags in sorted(by_form.items()):
        g, p = tags.get("sg g"), tags.get("sg p")
        # EKI's mark is the key: genitive unmarked (II), partitive marked (III).
        if g is not None and p is not None and "`" not in g and "`" in p:
            out["valde"].append((form, "sg g", f"selle {form}", f"seda {form}"))
            out["valde"].append((form, "sg p", f"seda {form}", f"selle {form}"))

    forms = sorted(by_form)
    known = set(forms)
    tag_of = {f: next(iter(by_form[f])) for f in forms}
    for form in forms:
        for i, ch in enumerate(form):
            for group in _VOWELS:
                if ch not in group:
                    continue
                for other in sorted(group - {ch}):
                    twin = form[:i] + other + form[i + 1:]
                    if twin in known:
                        out["taht"].append((form, tag_of[form], form, twin))
            doubled = form[:i + 1] + ch + form[i + 1:]
            if doubled in known and ch not in _QUANTITY_LETTERS:
                out["pikkus"].append((form, tag_of[form], form, doubled))
                out["pikkus"].append((doubled, tag_of[doubled], doubled, form))
    return out


def _everyday(words: sqlite3.Connection | None, pairs: dict[str, list[tuple]]
              ) -> dict[str, list[tuple]]:
    """Keep pairs whose two forms are both forms of A1–A2 words (EKI's level, or
    the list's estimate); a rule left empty keeps all its pairs."""
    if words is None:
        return pairs
    from .morph import _readings

    try:
        known = {r[0] for r in words.execute(
            "SELECT word FROM words WHERE proficiency IN ('A1', 'A2')")}
    except sqlite3.Error:
        return pairs

    def everyday(form: str) -> bool:
        return any(lemma in known for lemma, _tag in _readings(form))

    out = {}
    for rule, found in pairs.items():
        kept = [p for p in found if everyday(p[0]) and everyday(p[3].split()[-1])]
        out[rule] = kept or found
    return out


def drills(count: int = 10, seed: int | None = None,
           rules: tuple[str, ...] | None = None,
           words: sqlite3.Connection | None = None) -> list[PatternDrill]:
    wanted = [r for r in (rules or BASE_RULES) if r in BASE_RULES]
    pairs = _everyday(words, _recorded_pairs())
    pool = [(rule, p) for rule in wanted for p in pairs[rule]]
    if not pool:
        return []
    rng = random.Random(seed)
    rng.shuffle(pool)
    out: list[PatternDrill] = []
    while len(out) < count:
        for rule, (form, tag, answer, other) in pool[:count - len(out)]:
            choices = [answer, other]
            rng.shuffle(choices)
            out.append(PatternDrill(
                f"Kuula ja vali: {BLANK}", answer, other, "", "kuula", rule,
                _WHY[rule], "tahestik", say=form, say_tag=tag,
                choices=tuple(choices), source_id=SOURCE_ID, translate=False))
    return out
