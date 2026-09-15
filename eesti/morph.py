"""Deterministic Estonian morphology via Vabamorf (EstNLTK).

A sensor, not a judge: Vabamorf says a word *is* partitive, not that it *should
have been* genitive (that needs telicity, which is semantics). It finds
candidates and supplies evidence; correctness is decided elsewhere.

Vabamorf is called directly rather than through estnltk's Text pipeline, which
fetches NLTK's punkt tokenizer over the network.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache

from estnltk.vabamorf.morf import Vabamorf, spellcheck, synthesize

# Vabamorf form tags for the genitive/partitive object contrast.
GENITIVE_SG = "sg g"
PARTITIVE_SG = "sg p"
PARTITIVE_PL = "pl p"

# Parts of speech that can head an object phrase.
OBJECT_POS = frozenset({"S", "A", "P", "N", "Y"})  # noun, adj, pronoun, numeral, abbrev

_TOKEN_RE = re.compile(r"\w+|[^\w\s]", re.UNICODE)
# A sentence boundary is `.`/`!`/`?` (optionally after a closing quote) followed
# by space and a word that is not lowercase: `28. augustil` stays whole, `2018.
# Seal` splits. Two lookbehinds because Python needs fixed widths.
_SENT_RE = re.compile(
    r"(?:(?<=[.!?])|(?<=[.!?][”\"»’\')\]]))\s+(?![a-zäöüõšž])"
)


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
    """Analyse text, keeping character offsets so the UI highlights the exact span."""
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
        tokens.append(
            Token(
                text=surface,
                lemma=best.get("lemma", surface),
                pos=best.get("partofspeech", ""),
                form=best.get("form", ""),
                start=start,
                end=end,
            )
        )
    return tokens


def object_case_candidates(text: str) -> list[Token]:
    """Tokens that sit in a possible object slot and carry genitive/partitive; both
    directions of the error are flagged for the provider to adjudicate.
    """
    return [
        t
        for t in analyze(text)
        if t.could_be_object and (t.is_partitive or t.is_genitive_sg)
    ]


def _readings(word: str) -> set[tuple[str, str]]:
    """All (lemma, form) readings of a surface form, without disambiguation, which
    would hide the alternative being checked.
    """
    out: set[tuple[str, str]] = set()
    for item in _vm().analyze([word], disambiguate=False, guess=False, propername=False):
        for opt in item.get("analysis") or []:
            out.add((opt.get("lemma", ""), opt.get("form", "")))
    return out


@lru_cache(maxsize=4096)
def case_forms(lemma: str) -> dict[str, str]:
    """Genitive and partitive singular for a lemma, or {} if either is unknown.

    Each synthesised candidate is re-analysed and kept only if it reads back as
    this lemma in this case (`kool` also yields `koola`). Exactly one survivor is
    required: several means the answer is unknown, and a wrong answer key is worse
    than no drill.
    """
    out: dict[str, str] = {}
    for key, tag in (("genitive", GENITIVE_SG), ("partitive", PARTITIVE_SG)):
        candidates = {
            c for c in (synthesize(lemma, tag) or []) if (lemma, tag) in _readings(c)
        }
        # No tie-breaking: homographs (`reis` the journey vs the thigh) and free variants
        # (`kaht`/`kahte`) cannot be separated by morphology, so they are refused.
        if len(candidates) != 1:
            return {}
        out[key] = candidates.pop()
    return out


def has_distinct_object_cases(lemma: str) -> bool:
    """True when genitive != partitive, i.e. the contrast is actually testable."""
    forms = case_forms(lemma)
    return bool(forms) and forms["genitive"] != forms["partitive"]


def misspellings(text: str) -> list[dict]:
    """Offline spellcheck with suggestions. Free signal, no network."""
    words = [w for w in tokenize(text) if w.isalpha()]
    if not words:
        return []
    return [r for r in spellcheck(words, suggestions=True) if not r["spelling"]]

# ---------------------------------------------------------------------------
# Subject-verb agreement
# ---------------------------------------------------------------------------
#
# `ma elab` is wrong from the morphology of two adjacent words, so it can be
# corrected, with the form synthesised by Vabamorf.
#
# The rules and their exceptions follow GiellaLT's Estonian Constraint Grammar
# (`giellalt/lang-est-x-utee`, LGPL-3.0, `&err-agr`); only the linguistic analysis
# is reused, not its toolchain.
#
# Finite verb forms by tense/mood, in person order 1sg, 2sg, 3sg, 1pl, 2pl, 3pl,
# as Vabamorf emits them (regenerated in `tests/test_agreement.py`).
_FINITE = (
    ("n", "d", "b", "me", "te", "vad"),            # olevik
    ("sin", "sid", "s", "sime", "site", "sid"),    # lihtminevik
    ("ksin", "ksid", "ks", "ksime", "ksite", "ksid"),  # tingiv kõneviis
)

#: Vabamorf encodes person as the pronoun's *lemma* and number as its case tag:
#: `me` analyses as `mina` + `pl n`, not as a lemma of its own.
_PERSON = {
    ("mina", "sg"): 0, ("sina", "sg"): 1, ("tema", "sg"): 2,
    ("mina", "pl"): 3, ("sina", "pl"): 4, ("tema", "pl"): 5,
}

#: `sid` and `ksid` are 2sg **and** 3pl ("sa elasid" is correct), per GiellaLT.
_FORM_PERSONS: dict[str, set[int]] = {}
for _group in _FINITE:
    for _i, _tag in enumerate(_group):
        _FORM_PERSONS.setdefault(_tag, set()).add(_i)

#: Particles that flip a following clause into the imperative, where the
#: person marking stops applying. GiellaLT excludes them explicitly:
#: "excl. eks|ega ma ela".
_IMPERATIVE_PARTICLES = frozenset({"eks", "ega"})


@dataclass(frozen=True)
class Disagreement:
    """A pronoun and a verb that cannot both be right."""

    pronoun: str
    verb: str
    #: What the verb should be, synthesised — empty if Vabamorf cannot make it.
    correct: str
    start: int
    end: int


def agreement_errors(text: str) -> list[Disagreement]:
    """Personal pronoun immediately followed by a verb in the wrong person.

    Narrow, because a false positive tells a learner correct Estonian is wrong:
    a nominative personal pronoun; the immediately following token; a finite verb
    form; a form ambiguous between persons agrees with both; `eks`/`ega` before
    the pronoun suppress the check. Negation needs no case: the connegative has no
    person tag.
    """
    found: list[Disagreement] = []
    for sentence in split_sentences(text) or [text]:
        tokens = [t for t in analyze(sentence) if t.pos != "Z"]
        offset = text.find(sentence)
        for i, token in enumerate(tokens[:-1]):
            if token.pos != "P":
                continue
            number, _, case = (token.form or "").partition(" ")
            if case != "n":
                continue
            person = _PERSON.get((token.lemma, number))
            if person is None:
                continue
            if i and tokens[i - 1].text.casefold() in _IMPERATIVE_PARTICLES:
                continue

            verb = tokens[i + 1]
            if verb.pos != "V":
                continue
            allowed = _FORM_PERSONS.get(verb.form or "")
            if not allowed or person in allowed:
                continue

            group = next(g for g in _FINITE if verb.form in g)
            candidates = synthesize(verb.lemma, group[person], "V") or []
            at = sentence.find(verb.text)
            found.append(Disagreement(
                pronoun=token.text,
                verb=verb.text,
                correct=candidates[0] if candidates else "",
                start=offset + at if offset >= 0 and at >= 0 else -1,
                end=offset + at + len(verb.text) if offset >= 0 and at >= 0 else -1,
            ))
    return found
