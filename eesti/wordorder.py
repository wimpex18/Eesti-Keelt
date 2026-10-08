"""Word order: attested learner corrections as a two-way choice.

`word-order` is the second-largest annotated error class in the EVKK learner
corpus, after `vocab`.

Items are attested, not generated. Swapping constituents to make a V2
distractor fails: in native text a leading adverb often modifies the subject
rather than being fronted, and telling those apart is syntax, which this
project does not have. A distractor that is sometimes correct Estonian teaches
the wrong rule.

So items come from pairs where a learner wrote a sentence and a native
corrected it, filtered to corrections that only re-order (`is_reordering`):

- TalTechNLP `grammar_et` (test and train splits) and `grammar2_et`;
- EstGEC-L2 (`eesti/estgec.py`), which labels word order (`R:WO`) and gives
  the writer's CEFR level.

`is_reordering` is the single gate for every source. The eval track
(`evals/external.py`) reads only the `grammar_et` test split, so the drill pool
does not change its benchmark. Neither dataset states a licence: personal
study, git-ignored, never redistributed.
"""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from .item import GradedItem

#: The nine-tag vocabulary the Notion log uses.
TAG = "word-order"

SOURCE_ID = "taltech-gec"

#: Every source the drill draws from; all pass the same `is_reordering` gate.
SOURCE_IDS = (SOURCE_ID, "estgec-l2")

#: Finite verb form tags in Vabamorf's vocabulary. `neg` (the particle `ei`) is
#: excluded: it is tagged V but is not the finite verb whose position is at
#: issue.
FINITE = frozenset({
    "b", "vad", "n", "d", "me", "te", "s", "sin", "sid", "sime", "site",
    "sivad", "takse", "kse", "ks", "ksin", "ksid", "ksime", "ksite",
    "ksivad", "o",
})

_WORD = re.compile(r"[^\w\sõäöüÕÄÖÜ-]", re.UNICODE)

def _words(text: str) -> list[str]:
    return _WORD.sub(" ", text).lower().split()


def _punctuation(text: str) -> list[str]:
    """Everything `_words` throws away — the same pattern, read the other way."""
    return sorted(_WORD.findall(text))


def is_reordering(wrong: str, right: str) -> bool:
    """True when the correction only moved words about.

    The multiset of words and the punctuation are unchanged. Punctuation matters:
    the learner chooses between the two sentences, so any visible difference other
    than order would be answerable without knowing the rule.
    """
    a, b = _words(wrong), _words(right)
    if not a or a == b or sorted(a) != sorted(b):
        return False
    return _punctuation(wrong) == _punctuation(right)


@dataclass(frozen=True)
class Item:
    wrong: str
    right: str
    rule: str                # v2 | negation | other
    why_ru: str
    moved: str = ""
    #: CEFR level of the learner who wrote it, where the source says (EstGEC-L2
    #: only); `None` otherwise.
    level: str | None = None

    @property
    def key(self) -> str:
        import hashlib

        return hashlib.sha1(self.right.encode()).hexdigest()[:16]

    def to_dict(self) -> dict:
        return {
            "key": self.key, "wrong": self.wrong, "right": self.right,
            "rule": self.rule, "why_ru": self.why_ru, "moved": self.moved,
            "level": self.level, "tag": TAG,
        }


#: Russian, like every explanation the learner has to act on. Each says what
#: moved and why, and the general one is deliberately modest: it claims a
#: native's preference, not a grammatical verdict.
WHY = {
    # "обычно", not "всегда": EKK (SÜ 92) says the finite verb is *usually* second
    # and inversion is a means of emphasis.
    "v2": (
        "**Спрягаемый глагол — вторым.** Если предложение начинается не с "
        "подлежащего (время, место, дополнение), подлежащее обычно уходит "
        "*после* глагола: «Eile **läksin ma** kooli», а не «Eile ma läksin». "
        "В русском порядок свободный — отсюда и ошибка. Это сильная тенденция, "
        "а не железное правило: инверсия в эстонском ещё и способ выделить "
        "нужное слово (EKK, SÜ 92)."
    ),
    "negation": (
        "**Отрицание.** Частица `ei` стоит непосредственно перед глаголом, "
        "между ними ничего не вставляют: «Keegi **ei leia** kunagi», а не "
        "«Keegi kunagi ei leia»."
    ),
    "other": (
        "Так написал носитель языка, исправляя это предложение. Порядок слов "
        "в эстонском гибкий, поэтому здесь речь не о грамматической ошибке, а "
        "о том, что звучит естественно — а именно это и оценивают на экзамене."
    ),
}


def _finite_index(tokens) -> int | None:
    for i, tok in enumerate(tokens):
        if tok.pos == "V" and tok.form in FINITE:
            return i
    return None


def classify(wrong: str, right: str) -> tuple[str, str]:
    """Name the rule the correction illustrates, and the word that moved.

    Only verb-second and `ei` before its verb can be read off morphology; anything
    else is `other` (a native moved it, not a broken rule).
    """
    from .morph import analyze

    tw = [t for t in analyze(wrong) if t.pos != "Z"]
    tr = [t for t in analyze(right) if t.pos != "Z"]
    iw, ir = _finite_index(tw), _finite_index(tr)

    moved = ""
    for a, b in zip(_words(wrong), _words(right)):
        if a != b:
            moved = b
            break

    # `ei` immediately before its verb in the correction but not in the error.
    def negation_gap(tokens) -> bool:
        for i, tok in enumerate(tokens[:-1]):
            if tok.pos == "V" and tok.form == "neg":
                return tokens[i + 1].pos != "V"
        return False

    if negation_gap(tw) and not negation_gap(tr):
        return "negation", moved
    if ir == 1 and iw is not None and iw > 1:
        return "v2", moved
    return "other", moved


def from_pairs(pairs) -> list[Item]:
    """Build items from (learner wrote, native corrected[, level]) tuples."""
    out: list[Item] = []
    for pair in pairs:
        wrong, right = pair[0], pair[1]
        level = pair[2] if len(pair) > 2 else None
        if not is_reordering(wrong, right):
            continue
        rule, moved = classify(wrong, right)
        out.append(Item(wrong=wrong.strip(), right=right.strip(),
                        rule=rule, why_ru=WHY[rule], moved=moved, level=level))
    return out


def load(path: Path | str) -> list[Item]:
    """Read `grammar_et` from disk and keep only the re-orderings; a missing file
    yields no items.
    """
    path = Path(path)
    if not path.exists():
        return []
    try:
        rows = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return from_pairs([(r.get("original", ""), r.get("correct", ""))
                       for r in rows])


def bench_files(bench_dir: Path | str | None = None) -> list[Path]:
    """Every fetched (learner wrote, native corrected) file, newest source last.

    Derived from `evals.fetch.DATASETS`: every GEC pair file shares the `original`,
    `correct` shape. Unfetched files are included; `load` treats absence as empty.
    """
    from .evals.fetch import BENCH_DIR, DATASETS

    root = Path(bench_dir or BENCH_DIR)
    return [root / f"{name}.json" for name in DATASETS if name.startswith("grammar")]


def items(content: sqlite3.Connection | None, limit: int = 10,
          seed: int | None = None) -> list[Item]:
    """Word-order items from the content store, hardest rule first.

    Ordered v2 → negation → other so a session opens with the two that carry a
    rule rather than with a stylistic preference.
    """
    import random

    if content is None:
        return []
    try:
        placeholders = ",".join("?" for _ in SOURCE_IDS)
        rows = content.execute(
            f"SELECT body, meta, level FROM items"
            f" WHERE source_id IN ({placeholders}) AND skill = ?",
            (*SOURCE_IDS, "kirjutamine"),
        ).fetchall()
    except sqlite3.Error:
        return []

    out: list[Item] = []
    for row in rows:
        body = row[0] if not isinstance(row, sqlite3.Row) else row["body"]
        meta = row[1] if not isinstance(row, sqlite3.Row) else row["meta"]
        level = row[2] if not isinstance(row, sqlite3.Row) else row["level"]
        try:
            data = json.loads(meta or "{}")
        except ValueError:
            continue
        if not data.get("wrong"):
            continue
        out.append(Item(wrong=data["wrong"], right=body, rule=data.get("rule", "other"),
                        why_ru=WHY.get(data.get("rule", "other"), WHY["other"]),
                        moved=data.get("moved", ""), level=level))

    rank = {"v2": 0, "negation": 1, "other": 2}
    random.Random(seed).shuffle(out)
    out.sort(key=lambda i: rank.get(i.rule, 9))
    return out[:limit]


def grade(item: Item, chosen: str) -> bool:
    """Server-side, like every other answer in this app."""
    return " ".join(_words(chosen)) == " ".join(_words(item.right))


def ingest(content: sqlite3.Connection, path: Path | str) -> int:
    """Put the pairs into the content store (`content.db`).

    Owner-only material reaches a deployment via `deploy/push-content.sh`, never an
    image. The corrected sentence is the body; the learner's version and the rule
    ride in `meta`.
    """
    from .sources import register

    register(content)
    found = load(path)
    if not found:
        return 0
    return _store(content, found, SOURCE_ID)


def ingest_estgec(content: sqlite3.Connection,
                  cache_dir: Path | str | None = None) -> int:
    """EstGEC-L2 pairs, through `from_pairs` so `is_reordering` gates them too."""
    from . import estgec
    from .sources import register

    register(content)
    found = from_pairs(estgec.pairs(cache_dir))
    return _store(content, found, estgec.SOURCE_ID) if found else 0


def _store(content: sqlite3.Connection, found: list[Item], source_id: str) -> int:
    from .sources import Item as SourceItem
    from .sources import add_items

    return add_items(content, [
        SourceItem(
            source_id=source_id, skill="kirjutamine", body=i.right,
            title=f"sõnajärg: {i.rule}", level=i.level,
            meta={"wrong": i.wrong, "rule": i.rule, "moved": i.moved,
                  "tag": TAG, "kind": "harjutus"},
        )
        for i in found
    ])


# ---------------------------------------------------------------------------
# The practice-loop shape
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class WordOrderItem(GradedItem):
    """One attested correction, as a two-way choice.

    Blanking a word does not fit word order (the answer would be recoverable by
    elimination), so the item carries `choices` — the two sentences. Grading is
    the usual string comparison, so mastery and review work unchanged.
    """

    prompt: str
    answer: str
    distractor: str
    lemma: str = ""
    topic: str = "sonajark"
    rule: str = "other"
    why_ru: str = ""
    choices: tuple[str, ...] = ()

    @property
    def label(self) -> str:
        return {"v2": "sõnajärg: pöördsõna teisel kohal",
                "negation": "sõnajärg: eitus",
                "other": "sõnajärg"}.get(self.rule, "sõnajärg")

    @property
    def hint(self) -> str:
        # The lemma slot would normally name the word being asked for. Here
        # there is no single word, so the hint names the rule instead.
        return self.label


def generate(count: int = 10, seed: int | None = None,
             content: sqlite3.Connection | None = None,
             path: Path | str | None = None) -> list[WordOrderItem]:
    """Practice items for `sonajark`, hardest rule first: from the content store when
    present (deployment), else the raw file (local).
    """
    import random

    pool = items(content, limit=1000, seed=seed) if content is not None else []
    if not pool and path is not None:
        pool = load(path)
    if not pool:
        return []

    rank = {"v2": 0, "negation": 1, "other": 2}
    rng = random.Random(seed)
    rng.shuffle(pool)
    pool.sort(key=lambda i: rank.get(i.rule, 9))

    out: list[WordOrderItem] = []
    for item in pool[:count]:
        # Shuffle the two options so position cannot give the answer away.
        choices = [item.right, item.wrong]
        rng.shuffle(choices)
        out.append(WordOrderItem(
            prompt="Kumb lause on õige?",
            answer=item.right,
            distractor=item.wrong,
            rule=item.rule,
            why_ru=item.why_ru,
            choices=tuple(choices),
        ))
    return out


# ---------------------------------------------------------------------------
# Public tiles: EKI's phrases, rebuilt in order
# ---------------------------------------------------------------------------
#
# The attested corrections above are not redistributable, so a learner outside
# the owner's scope gets none. EVS's example phrases are (CC BY 4.0): the
# learner is given the Russian and the Estonian words out of order and rebuilds
# EKI's phrase. Nothing is generated but the shuffle, so no distractor can be
# accidentally correct Estonian. The risk is the other way round: an order
# EKI did not print would be marked wrong, and clause order is flexible (`sa
# pead tema ees vabandama` ~ `sa pead vabandama tema ees`; EKK SÜ 92 calls
# inversion a means of emphasis, not an error). So only the order EKK fixes is
# built: the noun phrase, whose adjective and genitive attributes stand before
# their head (EKK SÜ 98, 99). Within it EKK SÜ 104 names two free orders, an
# adjective beside a genitive (`luksuslikud Fazeri ~ Fazeri luksuslikud
# šokolaadikarbid`) and a cardinal beside an ordinal (`viis viimast ~ viimased
# viis`), and two descriptive adjectives can swap too; none of those is built.
# What remains is mostly the genitive chain (`laulja populaarsuse saladus`,
# `kolme lapse isa`) and a determiner with one adjective (`minu kunagine
# klassiõde`).

#: Words and a final question or exclamation mark: anything else inside the
#: phrase (a comma, a quotation mark, `3.`) would be lost from the tiles.
_TILEABLE = re.compile(r"[\w'-]+(?: [\w'-]+)*[?!]?", re.UNICODE)

#: Vabamorf's parts of speech that can move within a clause: verb, adverb,
#: conjunction, interjection, and the unanalysable (abbreviation, foreign, symbol).
_FREE = frozenset({"V", "D", "J", "I", "X", "Y", "Z"})

#: Descriptive attributes: adjective, comparative, superlative, ordinal.
_DESCRIPTIVE = frozenset({"A", "C", "U", "O"})

_GENITIVE = frozenset({"sg g", "pl g"})
_NOMINATIVE = frozenset({"sg n", "pl n"})


def _fixed_order(phrase: str) -> bool:
    """Whether EKK fixes this phrase's word order (see above): a noun in the
    nominative last; before it, genitive attributes (a noun, name or pronoun
    with a genitive reading, or an indeclinable `G` such as *eesti*), numerals,
    and at most one descriptive attribute, which then stands with no genitive
    noun and no cardinal beside an ordinal. No word may have a reading whose
    place is free (`viis` is also *viima*); an unknown word counts as free.
    """
    from .morph import pos_readings

    words = phrase.rstrip("?!").split()
    # Part of speech and case come from the same reading: *null koma kuus* is
    # not a noun phrase because *kuus* is a noun (*kuu*) and a nominative (*kuus*).
    readings = [pos_readings(w) for w in words]
    pos = [{p for p, _ in r} - {""} for r in readings]
    if any(not p or p & _FREE for p in pos):
        return False

    def has(r, kinds, cases):
        return any(p in kinds and f in cases for p, f in r)

    if not has(readings[-1], {"S"}, _NOMINATIVE):
        return False
    descriptive = genitives = 0
    for p, r in zip(pos[:-1], readings[:-1]):
        if p & _DESCRIPTIVE:
            descriptive += 1
            if not has(r, _DESCRIPTIVE, _NOMINATIVE | _GENITIVE):
                return False
        elif "N" in p:
            if not has(r, {"N"}, _NOMINATIVE | _GENITIVE):
                return False
        elif "G" in p:
            genitives += 1
        elif has(r, {"S", "H", "P"}, _GENITIVE):
            genitives += "P" not in p
        else:
            return False
    attributes = set().union(*pos[:-1])
    return descriptive <= 1 and not (descriptive and genitives) and not (
        "N" in attributes and "O" in attributes)


@dataclass(frozen=True)
class PhraseTiles(GradedItem):
    """One EVS phrase to rebuild from its words. `prompt` lists the tiles, so a
    review card or a test-out that shows only the prompt can still be answered.
    """

    prompt: str
    answer: str          # EKI's phrase, words only
    ru: str              # EKI's Russian for it
    tiles: tuple[str, ...]
    lemma: str = ""      # the EVS headword the phrase illustrates
    distractor: str = ""
    topic: str = "sonajark"
    rule: str = "evs-order"
    why_ru: str = ""
    source_id: str = "eki-evs"
    choices: tuple[str, ...] = ()

    @property
    def label(self) -> str:
        return "sõnajärg: fraas"

    @property
    def hint(self) -> str:
        return self.label


def _tiles_why(estonian: str, russian: str) -> str:
    return ("**Порядок слов (sõnajärg)** в именной группе: определение в "
            "omastav и согласованное прилагательное стоят перед главным "
            f"словом (EKK SÜ 98). Пример EKI: «{estonian}» — «{russian}».")


def phrase_tiles(phrases, count: int = 10, seed: int | None = None) -> list[PhraseTiles]:
    """Tile items for `sonajark` from `evs.phrases`: the Russian is given, EKI's
    Estonian is rebuilt from its shuffled words. Only phrases of fixed order
    (`_fixed_order`); one whose words have no other order (all the same word)
    is skipped.
    """
    import random

    from .evs import SOURCE_ID, buildable

    rng = random.Random(seed)
    # EKI writes phrases in lower case; a capital is a proper name (*Nobeli*),
    # which is not the order being practised.
    pool = [p for p in phrases if buildable(p.estonian) and _TILEABLE.fullmatch(p.estonian)
            and not any(w[:1].isupper() for w in p.estonian.split())]
    rng.shuffle(pool)
    out: list[PhraseTiles] = []
    for phrase in pool:
        if len(out) >= count:
            break
        if not _fixed_order(phrase.estonian):
            continue
        words = phrase.estonian.rstrip("?!").split()
        tiles = list(words)
        for _ in range(6):
            rng.shuffle(tiles)
            if tiles != words:
                break
        if tiles == words:
            continue
        out.append(PhraseTiles(
            prompt=" / ".join(tiles),
            answer=" ".join(words),
            ru=phrase.russian,
            tiles=tuple(tiles),
            lemma=phrase.lemma,
            why_ru=_tiles_why(phrase.estonian, phrase.russian),
            source_id=SOURCE_ID,
        ))
    return out
