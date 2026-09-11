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
# A sentence boundary is a `.`/`!`/`?` followed by space — *except* after a
# bare number, because that is how Estonian writes an ordinal. `28. augustil`,
# `Balti riikide 100. aastapäev`, `Eesti on 12. riik` were all being cut in
# half, which put 7 % truncated sentences and 5 % orphaned tails into the
# corpus pool. Harmless for a cloze that blanks one word; not harmless for
# dictation, where the learner is asked to write down "Maailmameister selgub
# pühapäeval, 28." and has no way to know what was cut off.
#
# The rule that covers both, and is simpler than special-casing digits: a
# sentence never *continues* with a lowercase word, so a period followed by one
# was not a boundary. `28. augustil` and `12. riik` stay whole; `Locked Shields
# 2018. Seal osales…` still splits, because `Seal` is capitalised and a year
# can genuinely end a sentence.
# The terminator may be followed by a closing quote — Estonian writes „…” and
# ERR uses it constantly — so the boundary is looked for after that too. Two
# lookbehinds rather than one alternation, because Python needs each to be a
# fixed width.
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

# ---------------------------------------------------------------------------
# Subject-verb agreement
# ---------------------------------------------------------------------------
#
# The one syntactic error class this project can check without syntax.
#
# `object_case_candidates` above reports the case a word is in and refuses to
# say whether it is the right one, because that needs telicity, which is
# semantics. Agreement is the opposite: `ma elab` is wrong for a reason that is
# entirely visible in the morphology of two adjacent words, and no amount of
# context makes it right. So it can be *corrected*, not merely flagged — and
# the correction is synthesised by the same Vabamorf that grades every drill.
#
# **Where the rules come from.** GiellaLT's Estonian grammar checker
# (`giellalt/lang-est-x-utee`, LGPL-3.0, morphology by Heiki-Jaan Kaalep at the
# University of Tartu) carries hand-written Constraint Grammar rules for this,
# tagged `&err-agr`. Their toolchain is not adopted — running those rules means
# running GiellaLT's own morphology beside Vabamorf, a second analyser and a
# second source of truth for the thing Vabamorf is the answer key for, plus
# HFST and VISL CG3 in the image. What is taken is the **linguistic analysis**:
# which pairs disagree, and, more valuable, which apparent disagreements are
# not errors. Those exceptions are in their rule comments and are reproduced
# below with attribution.
#
#: Finite verb forms by tense/mood, each in person order:
#: 1sg, 2sg, 3sg, 1pl, 2pl, 3pl.
#:
#: Read straight off Vabamorf's own output rather than a grammar book — see
#: the table in `tests/test_agreement.py`, which regenerates it.
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

#: `sid` and `ksid` are 2sg **and** 3pl. GiellaLT's rule comment says it
#: outright — "sa elasid, sa elaksid is OK" — and a checker that did not know
#: this would call correct Estonian wrong every time the learner used the past
#: tense with `sa`, which is the single most common thing to say.
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

    Deliberately narrow, because the cost of a false positive here is a learner
    being told correct Estonian is wrong:

    * only a **nominative personal pronoun** — a closed class of six;
    * only the **immediately** following token, so nothing is claimed about
      words that merely appear in the same sentence;
    * only a **finite** verb form, so infinitives, participles and the
      impersonal are left alone;
    * a form that is ambiguous between two persons agrees with **both**;
    * and `eks`/`ega` before the pronoun suppresses the check entirely.

    Negation needs no special case and gets none: `ma ei ela` analyses as `ei`
    plus a connegative, which carries no person tag and so is not in `_FINITE`.
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
