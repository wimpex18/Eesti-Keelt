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
it**: TalTechNLP's `grammar_et` and `grammar2_et`, filtered to corrections that
only re-order — same words, different sequence. Correctness is given rather
than inferred. Nothing is claimed about the learner's version being
ungrammatical; the question asked is which one a native wrote, which is also
how the exam is marked.

The filter is severe, and that is the cost of refusing to generate. Which
makes the size of the pool being filtered the only lever there is:

| pairs | items |
|---|---|
| `grammar_et` test, 1 000 | 43 |
| `grammar2_et` train, 446 | 12 |
| `grammar_et` **train, 7 937** | **267** |
| | **322** |

Measured 2026-09-11, and the interesting row is the third. Nothing had ever
fetched it. `grammar_et` has two splits; `evals/external.py` scores the test
one, so the fetch table named that split and every later pass read the fetch
table. Eight times the pairs were sitting behind a word nobody had reason to
re-read. `grammar2_et` — same two columns, published 2024-11-18 — was missed
the same way: the benchmark paper lists seven datasets and it is an eighth
beside them.

The eval track still reads the test file and only the test file. The splits are
disjoint and land in separate files, so what that track scores has not moved —
a pool five times bigger would otherwise have arrived as a mysteriously
different benchmark number.

A second corpus, and why it was merged rather than swapped in
-------------------------------------------------------------
`EstGEC-L2` (Tallinn University, GPL-3.0) annotates word order as **`R:WO`**
instead of leaving it to be inferred, and publishes its test split per CEFR
level. See `eesti/estgec.py`. It adds 242 items and brings the pool to 564,
of which 157 now say what level their writer was sitting at — the first items
here that do.

Both questions were measured before either was answered:

* the two corpora share **not one** corrected sentence, so replacing would have
  discarded 322 items and bought nothing;
* **232 of EstGEC-L2's 237** pass `is_reordering` unchanged, so merging does
  not put two standards of item in one pool.

`is_reordering` stays the single gate. A labelled `R:WO` does not exempt a pair
from it: `pealinn Islandil` → `Islandi pealinn` is annotated word order and
also changes a case ending, and the learner could answer that from the ending.
One bar, two feeders, and a new source cannot lower it by arriving.

Licence: neither dataset card states one. Treated like every other ungranted
source here — personal study, git-ignored, never redistributed, and never baked
into an image built from a public repository.
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

#: Every source the drill draws from. Two, since 2026-09-12, and merged rather
#: than swapped because the question was measured before it was answered: the
#: two corpora share **not one** corrected sentence, so replacing would have
#: thrown 322 items away for nothing, and 232 of EstGEC-L2's 237 pass
#: `is_reordering` unchanged, so merging does not mix two standards of item.
#: One gate, two feeders -- a new source cannot lower the bar by arriving.
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

    The signature of a word-order error, and the reason it can be told apart
    from every other kind of correction without an annotation layer: the
    multiset of words is unchanged.

    Punctuation has to be unchanged too, and that is not pedantry. The item is
    a two-way choice between the learner's sentence and the native's, asking
    which one an Estonian wrote — so any difference the learner can see is a
    difference the learner can answer on. A pair that moves two words *and*
    adds a comma is answerable from the comma, and would be teaching comma
    placement under a label that says `sõnajärg`. 54 of 376 pairs are that
    shape (measured 2026-09-11); dropping them costs a seventh of the pool and
    buys items where the only visible difference is the one being taught.
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
    #: CEFR level of the learner who wrote it, where the source says.
    #:
    #: `None` for every TalTech pair, because that file does not say and this
    #: project does not invent a scale it was not given. EstGEC-L2 publishes its
    #: test split per level, so those arrive labelled -- which is most of what
    #: that corpus adds over an inference.
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


def from_pairs(pairs) -> list[Item]:
    """Build items from (learner wrote, native corrected[, level]) tuples.

    The level is optional so both feeders use one function: TalTech's file has
    no level to give, EstGEC-L2's test split has one per sentence.
    """
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


def bench_files(bench_dir: Path | str | None = None) -> list[Path]:
    """Every fetched (learner wrote, native corrected) file, newest source last.

    Derived from `evals.fetch.DATASETS` rather than listed here, because a
    hand-kept copy of a list that already exists is this project's
    most-repeated bug. Every GEC pair file shares one two-column shape --
    `original`, `correct` -- so the same reader takes all of them, and a file
    added to the fetch table is ingested without touching this. That is how
    `grammar_et`'s train split arrived: one line there, three files here.

    Files that were never fetched are returned anyway: `load` treats absence as
    empty, which is what makes a fresh checkout work.
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
    return _store(content, found, SOURCE_ID)


def ingest_estgec(content: sqlite3.Connection,
                  cache_dir: Path | str | None = None) -> int:
    """The same, for the corpus that labels its word-order errors.

    Through `from_pairs`, so `is_reordering` gates these exactly as it gates
    TalTech's: one bar, and a second feeder cannot lower it.
    """
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
