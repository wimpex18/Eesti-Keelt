"""Word order: the second-biggest real error class, and the one with no drill.

The learner corpus is unambiguous about priority. Of the 51 467 errors
annotated in EVKK, `word-order` takes 11.4 % of all marks and 19.3 % of the
marks these nine tags cover — second only to `vocab` on either denominator —
and it was one of three tags in the error log that nothing in this app could
practise. (For contrast, `obj-case`, the documented weakness in *this*
learner's own log, is 1.3 % / 2.1 %. A personal log and a population disagree,
which is why both are kept.)

Why the items are attested rather than generated
------------------------------------------------
Every other drill here is generated: take a corpus sentence, blank a word,
compute the answer. The obvious version of that for word order is to take a
sentence, swap two constituents, and offer the swap as the wrong answer.

That was tried and abandoned, with a measurement. The rule it would teach is
V2 — in a declarative main clause the finite verb comes second, so when
something else is fronted the subject follows the verb:

    ✗ Oktoobris vihmased päevad vahelduvad kirgastega.
    ✓ Oktoobris vahelduvad vihmased päevad kirgastega.

Measured against 1 000 native-corrected sentences, restricted to single-clause
declaratives opening with an apparently fronted element: **75.4 % invert, 24.6 %
do not.** Inspecting the non-inverting quarter shows almost all of them are not
counter-examples to V2 at all — they are `Just ühiskond on…`, `Peaaegu kõik
mehed tahavad…`, `Eriti märgatav samm on…`, where the leading adverb modifies
the *subject* rather than being a fronted constituent. Telling those two apart
is syntax, and this project has morphology. It is the same boundary Vabamorf
already has with object case: it can report that a word is partitive and cannot
know it should have been genitive.

So generation is refused. A distractor that is sometimes correct Estonian would
teach the wrong rule, which is the one failure mode the plan names for this
whole tool.

Items come instead from pairs where **a learner wrote it and a native corrected
it**: TalTechNLP's `grammar_et`, filtered to corrections that only re-order —
same words, different sequence. Correctness is given rather than inferred.
Nothing is claimed about the learner's version being ungrammatical; the
question asked is which one a native wrote, which is also how the exam is
marked.

Licence: `grammar_et` states none. Treated like every other ungranted source
here — personal study, git-ignored, never redistributed, and never baked into
an image built from a public repository.
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


def is_reordering(wrong: str, right: str) -> bool:
    """True when the correction only moved words about.

    The signature of a word-order error, and the reason it can be told apart
    from every other kind of correction without an annotation layer: the
    multiset of words is unchanged.
    """
    a, b = _words(wrong), _words(right)
    return bool(a) and a != b and sorted(a) == sorted(b)


@dataclass(frozen=True)
class Item:
    wrong: str
    right: str
    rule: str                # v2 | negation | other
    why_ru: str
    moved: str = ""

    @property
    def key(self) -> str:
        import hashlib

        return hashlib.sha1(self.right.encode()).hexdigest()[:16]

    def to_dict(self) -> dict:
        return {
            "key": self.key, "wrong": self.wrong, "right": self.right,
            "rule": self.rule, "why_ru": self.why_ru, "moved": self.moved,
            "tag": TAG,
        }


#: Russian, like every explanation the learner has to act on. Each says what
#: moved and why, and the general one is deliberately modest: it claims a
#: native's preference, not a grammatical verdict.
WHY = {
    # Deliberately "обычно", not "всегда". EKK (SÜ 90) says the finite verb is
    # *usually* second and calls inversion a means of emphasis rather than a
    # rule; measuring 1 000 native-corrected sentences here gave 75.4 %
    # inversion in the shape this drill uses. Stating it as absolute would
    # teach a harder rule than the handbook does — and the learner would then
    # "correct" perfectly good Estonian.
    "v2": (
        "**Спрягаемый глагол — вторым.** Если предложение начинается не с "
        "подлежащего (время, место, дополнение), подлежащее обычно уходит "
        "*после* глагола: «Eile **läksin ma** kooli», а не «Eile ma läksin». "
        "В русском порядок свободный — отсюда и ошибка. Это сильная тенденция, "
        "а не железное правило: инверсия в эстонском ещё и способ выделить "
        "нужное слово (EKK, SÜ 90)."
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

    Only two rules are claimed, because only two can be read off morphology
    with confidence: the finite verb arriving in second position, and `ei`
    closing up against its verb. Everything else is `other`, which is honest —
    it says a native moved this, not that the learner broke a rule.
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


def from_pairs(pairs: list[tuple[str, str]]) -> list[Item]:
    """Build items from (learner wrote, native corrected) pairs."""
    out: list[Item] = []
    for wrong, right in pairs:
        if not is_reordering(wrong, right):
            continue
        rule, moved = classify(wrong, right)
        out.append(Item(wrong=wrong.strip(), right=right.strip(),
                        rule=rule, why_ru=WHY[rule], moved=moved))
    return out


def load(path: Path | str) -> list[Item]:
    """Read `grammar_et` from disk and keep only the re-orderings.

    Absence is a supported state: the file is owner-only and git-ignored, so a
    fresh checkout has no items and says so rather than failing.
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
        rows = content.execute(
            "SELECT body, meta FROM items WHERE source_id = ? AND skill = ?",
            (SOURCE_ID, "kirjutamine"),
        ).fetchall()
    except sqlite3.Error:
        return []

    out: list[Item] = []
    for row in rows:
        body = row[0] if not isinstance(row, sqlite3.Row) else row["body"]
        meta = row[1] if not isinstance(row, sqlite3.Row) else row["meta"]
        try:
            data = json.loads(meta or "{}")
        except ValueError:
            continue
        if not data.get("wrong"):
            continue
        out.append(Item(wrong=data["wrong"], right=body, rule=data.get("rule", "other"),
                        why_ru=WHY.get(data.get("rule", "other"), WHY["other"]),
                        moved=data.get("moved", "")))

    rank = {"v2": 0, "negation": 1, "other": 2}
    random.Random(seed).shuffle(out)
    out.sort(key=lambda i: rank.get(i.rule, 9))
    return out[:limit]


def grade(item: Item, chosen: str) -> bool:
    """Server-side, like every other answer in this app."""
    return " ".join(_words(chosen)) == " ".join(_words(item.right))


def ingest(content: sqlite3.Connection, path: Path | str) -> int:
    """Put the pairs into the content store.

    They travel to a deployment the way every other ungranted thing does — in
    `content.db`, pushed at runtime by `deploy/push-content.sh` — rather than
    baked into an image built from a public repository. The corrected sentence
    is the body; the learner's version and the rule ride in `meta`.
    """
    from .sources import Item as SourceItem
    from .sources import add_items, register

    register(content)
    found = load(path)
    if not found:
        return 0
    return add_items(content, [
        SourceItem(
            source_id=SOURCE_ID, skill="kirjutamine", body=i.right,
            title=f"sõnajärg: {i.rule}",
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

    Every other generator here blanks a word and asks for it. That shape does
    not fit word order: the unit being taught is the *sequence*, and blanking
    position two would leave the answer recoverable by elimination from the
    words still on screen.

    So the item carries `choices` — the two whole sentences — and the learner
    picks one. Grading is unchanged: `check` compares what was chosen against
    the answer, which is the same string comparison every other item uses, so
    this reaches mastery and the review queue through the existing path
    instead of needing a loop of its own.
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
    """Practice items for `sonajark`, hardest rule first.

    Reads the content store when there is one (that is how the items reach a
    deployment, riding `push-content.sh` like every other owner-only thing),
    and falls back to the raw file for local work.
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
        # Order of the two options is shuffled per item: a fixed position would
        # be learnable without reading either sentence.
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
