"""Deterministic Estonian morphology via Vabamorf (EstNLTK).

Scope note, deliberately narrow: Vabamorf tells us a word *is* partitive. It
cannot tell us it *should have been* genitive — that depends on whether the
action is completed (telic), which is semantics, not morphology. So this module
is a *sensor*, never the judge. It finds candidates and supplies hard evidence;
deciding correctness is the grammar provider's job.

We call Vabamorf directly rather than through estnltk's Text pipeline because
that pipeline pulls NLTK's punkt tokenizer over the network, which defeats the
offline-first goal (and is blocked in some sandboxes anyway).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache

from estnltk.vabamorf.morf import Vabamorf, spellcheck, synthesize

# Vabamorf form tags. Estonian marks the object with one of three cases;
# the genitive/partitive contrast is the one that carries aspect.
GENITIVE_SG = "sg g"
PARTITIVE_SG = "sg p"
PARTITIVE_PL = "pl p"
NOMINATIVE_SG = "sg n"

# Parts of speech that can head an object phrase.
OBJECT_POS = frozenset({"S", "A", "P", "N", "Y"})  # noun, adj, pronoun, numeral, abbrev

_TOKEN_RE = re.compile(r"\w+|[^\w\s]", re.UNICODE)
_SENT_RE = re.compile(r"(?<=[.!?])\s+")


def tokenize(text: str) -> list[str]:
    """Split into tokens without needing NLTK data."""
    return _TOKEN_RE.findall(text)


def split_sentences(text: str) -> list[str]:
    """Naive sentence split. Good enough — we never need perfect boundaries."""
    return [s.strip() for s in _SENT_RE.split(text.strip()) if s.strip()]


@dataclass(frozen=True)
class Token:
    text: str
    lemma: str
    pos: str
    form: str
    start: int
    end: int
    alternatives: tuple[tuple[str, str], ...] = field(default=())

    @property
    def is_genitive_sg(self) -> bool:
        return self.form == GENITIVE_SG

    @property
    def is_partitive(self) -> bool:
        return self.form in (PARTITIVE_SG, PARTITIVE_PL)

    @property
    def could_be_object(self) -> bool:
        return self.pos in OBJECT_POS


@lru_cache(maxsize=1)
def _vm() -> Vabamorf:
    return Vabamorf.instance()


def analyze(text: str) -> list[Token]:
    """Morphologically analyse text, keeping character offsets into the original.

    Offsets matter: the UI highlights the exact span the learner typed, so we
    locate each token in the source rather than trusting the tokenizer's order.
    """
    words = tokenize(text)
    if not words:
        return []
    analysed = _vm().analyze(words, disambiguate=True, guess=True, propername=True)

    tokens: list[Token] = []
    cursor = 0
    for item in analysed:
        surface = item["text"]
        start = text.find(surface, cursor)
        if start < 0:  # defensive: normalisation mismatch
            start = cursor
        end = start + len(surface)
        cursor = end

        options = item.get("analysis") or []
        best = options[0] if options else {}
        alts = tuple(
            sorted({(o.get("partofspeech", ""), o.get("form", "")) for o in options})
        )
        tokens.append(
            Token(
                text=surface,
                lemma=best.get("lemma", surface),
                pos=best.get("partofspeech", ""),
                form=best.get("form", ""),
                start=start,
                end=end,
                alternatives=alts,
            )
        )
    return tokens


def object_case_candidates(text: str) -> list[Token]:
    """Tokens that sit in a possible object slot and carry genitive/partitive.

    These are what the grammar provider must adjudicate. We flag both cases:
    a wrong genitive (should be partitive) is as much an obj-case error as the
    partitive-for-genitive one that dominates the error log.
    """
    return [
        t
        for t in analyze(text)
        if t.could_be_object and (t.is_partitive or t.is_genitive_sg)
    ]


def _readings(word: str) -> set[tuple[str, str]]:
    """All (lemma, form) readings of a surface form, without disambiguation.

    Disambiguation picks one reading and would hide the very alternative we are
    trying to confirm, so it must stay off here.
    """
    out: set[tuple[str, str]] = set()
    for item in _vm().analyze([word], disambiguate=False, guess=False, propername=False):
        for opt in item.get("analysis") or []:
            out.add((opt.get("lemma", ""), opt.get("form", "")))
    return out


@lru_cache(maxsize=4096)
def case_forms(lemma: str) -> dict[str, str]:
    """Genitive and partitive singular for a lemma, or {} if either is unknown.

    Vabamorf may return several candidates for an ambiguous string: synthesizing
    "kool" yields both 'kooli' (school) and 'koola' (cola, lemma "koola"). A
    prefix heuristic picks the wrong one, so we round-trip instead — analyse each
    candidate and keep it only if it reads back as this lemma in this case.

    Then, crucially, we require exactly **one** survivor. Zero and several are
    the same situation — we do not know the answer — and a wrong "correct
    answer" in a drill is worse than no drill.
    """
    out: dict[str, str] = {}
    for key, tag in (("genitive", GENITIVE_SG), ("partitive", PARTITIVE_SG)):
        candidates = {
            c for c in (synthesize(lemma, tag) or []) if (lemma, tag) in _readings(c)
        }
        # An earlier version broke ties by preferring the candidate with the
        # fewest competing lemma readings. That is right for "kool" — 'kooli'
        # reads only as *kool*, 'koola' also as the separate lemma *koola* — and
        # wrong for "reis", where it confidently returns the paradigm of *reis*
        # the thigh (reie, reit) over *reis* the journey (reisi), precisely
        # because the rarer word is the less ambiguous one. Two real words
        # spelled the same cannot be separated by morphology; only by meaning.
        #
        # The same refusal covers genuine free variants — 'kaht'/'kahte',
        # 'armast'/'armsat' — where a drill accepting one marks the other wrong.
        #
        # Measured cost: 111 of 2 570 A1-B1 nouns (4.3 %). Every one of them
        # would otherwise be an exercise with a confidently wrong answer.
        if len(candidates) != 1:
            return {}
        out[key] = candidates.pop()
    return out


def has_distinct_object_cases(lemma: str) -> bool:
    """True when genitive != partitive, i.e. the contrast is actually testable.

    For many Estonian nouns the two forms are identical ("maja"/"maja",
    "kooli"/"kooli"). Drilling those teaches nothing — the learner cannot get
    them wrong — so the drill generator uses this to filter its word pool.
    """
    forms = case_forms(lemma)
    return bool(forms) and forms["genitive"] != forms["partitive"]


def misspellings(text: str) -> list[dict]:
    """Offline spellcheck with suggestions. Free signal, no network."""
    words = [w for w in tokenize(text) if w.isalpha()]
    if not words:
        return []
    return [r for r in spellcheck(words, suggestions=True) if not r["spelling"]]
