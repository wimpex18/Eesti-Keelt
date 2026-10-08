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


#: Local (place and direction) cases. A word that may be one of them is not
#: offered as an object: *poodi* is the partitive and the short illative of
#: *pood*, and in *Ma pean minema poodi* it is "to the shop".
_LOCAL = frozenset({"adt", "ill", "in", "el", "all", "ad", "abl"})


def _may_be_local(token: Token) -> bool:
    return any(form.split()[-1] in _LOCAL
               for lemma, form in _readings(token.text) if lemma == token.lemma and form)


def object_case_candidates(text: str, takes_object=None) -> list[Token]:
    """Tokens that sit in a possible object slot and carry genitive/partitive; both
    directions of the error are flagged for the provider to adjudicate.

    With `takes_object` (`lemmas → those that take an object`), a word that may
    also be a place or direction (`_LOCAL`) is kept only when the nearest verb
    before it in its clause takes an object: *Ma söön leiba ära* keeps *leiba*,
    *Ma pean minema poodi* drops *poodi*.
    """
    tokens = analyze(text)
    if takes_object is not None:
        objects = set(takes_object(sorted({t.lemma for t in tokens if t.pos == "V"})))
    out, verb = [], None
    for t in tokens:
        if t.pos == "Z" or t.text.casefold() in _JOINS:
            verb = None
        elif t.pos == "V":
            verb = t
        if not (t.could_be_object and (t.is_partitive or t.is_genitive_sg)):
            continue
        if takes_object is not None and _may_be_local(t) and (
                verb is None or verb.lemma not in objects):
            continue
        out.append(t)
    return out


def _readings(word: str) -> set[tuple[str, str]]:
    """All (lemma, form) readings of a surface form, without disambiguation, which
    would hide the alternative being checked.
    """
    out: set[tuple[str, str]] = set()
    for item in _vm().analyze([word], disambiguate=False, guess=False, propername=False):
        for opt in item.get("analysis") or []:
            out.add((opt.get("lemma", ""), opt.get("form", "")))
    return out


def pos_readings(word: str) -> set[tuple[str, str]]:
    """Every (part of speech, form) reading of a surface form, without
    disambiguation: *kuus* is a noun only as *kuu* in the inessive, and a
    nominative only as the numeral, so the two must be read together.
    """
    out: set[tuple[str, str]] = set()
    for item in _vm().analyze([word], disambiguate=False, guess=False, propername=False):
        for opt in item.get("analysis") or []:
            out.add((opt.get("partofspeech", ""), opt.get("form", "")))
    return out


def parts_of_speech(word: str) -> set[str]:
    """Every part of speech a surface form can be, without disambiguation (`viis`
    is a numeral and a verb); empty when Vabamorf does not know the word.
    """
    out: set[str] = set()
    for item in _vm().analyze([word], disambiguate=False, guess=False, propername=False):
        for opt in item.get("analysis") or []:
            out.add(opt.get("partofspeech", ""))
    return out - {""}


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


def _guessed_forms(word: str) -> set[str]:
    """The forms Vabamorf's guesser reads in an unknown word, without its
    fallback of the whole word as a lemma (`Tallinas` → `sg in`)."""
    out: set[str] = set()
    for item in _vm().analyze([word], disambiguate=False, guess=True, propername=True):
        for opt in item.get("analysis") or []:
            if opt.get("lemma", "").casefold() != word.casefold() and opt.get("form"):
                out.add(opt["form"])
    return out


def _rank_suggestions(word: str, suggestions: list[str]) -> list[str]:
    """Vabamorf's suggestions, those that read back in a form the misspelling
    has first: *Tallinas* (an inessive) → *Tallinnas*, not *Tallina* (the
    essive of *tall*). Otherwise Vabamorf's own order is kept.
    """
    forms = _guessed_forms(word)
    if not forms or not suggestions:
        return list(suggestions)
    # Never promote an odd compound over Vabamorf's own first choice
    # (*jaksaama* → *jaks_jaama*).
    joins = _joins(suggestions[0])
    keeps = [s for s in suggestions
             if forms & {f for _, f in _readings(s)} and _joins(s) <= joins]
    return keeps + [s for s in suggestions if s not in keeps]


def _joins(word: str) -> int:
    """How many compound joins Vabamorf's simplest reading of a word has."""
    roots = [o.get("root", "") for item in _vm().analyze(
        [word], disambiguate=False, guess=False, propername=False)
        for o in item.get("analysis") or []]
    return min((r.count("_") for r in roots), default=0)


def misspellings(text: str) -> list[dict]:
    """Offline spellcheck with suggestions. Free signal, no network."""
    words = [w for w in tokenize(text) if w.isalpha()]
    if not words:
        return []
    return [{**r, "suggestions": _rank_suggestions(r["text"], r["suggestions"] or [])}
            for r in spellcheck(words, suggestions=True) if not r["spelling"]]


# ---------------------------------------------------------------------------
# An object written in the nominative
# ---------------------------------------------------------------------------
#
# The object (sihitis) is osastav or omastav; a nimetav total object needs an
# imperative, an impersonal or an infinitive construction (EKK). After a
# 1st/2nd-person indicative verb, or a negated verb with a 1st/2nd-person
# subject, none of those applies, and the subject cannot be a singular noun.

#: 1st/2nd-person indicative forms. `sid` is left out: it is also 3rd plural.
_PERSONAL = frozenset({"n", "d", "me", "te", "sin", "sime", "site"})
_SUBJECT_PRONOUNS = frozenset({"ma", "mina", "sa", "sina", "me", "meie", "te", "teie"})
#: Verbs whose nimetav complement is a predicative, not an object.
_PREDICATIVE = frozenset({"olema", "saama", "jääma", "hakkama"})
#: Nouns of time make a nimetav adverbial (*ootasin terve päev*), not an object.
_TIME = frozenset({"päev", "öö", "hommik", "õhtu", "nädal", "kuu", "aasta", "tund",
                   "minut", "sekund", "aeg", "kord", "talv", "suvi", "kevad", "sügis",
                   "lõuna", "pärastlõuna", "nädalavahetus"})
#: Verb forms that are not finite: a finite verb after the phrase means the
#: phrase is the next clause's subject (*arvan eesti keel on raske*).
_NONFINITE = frozenset({"ma", "mas", "mast", "mata", "maks", "da", "des", "nud", "tud",
                        "v", "tav", "tuv", "mine"})
#: Where a clause ends: punctuation or a clause-joining word.
_JOINS = frozenset({"ja", "ning", "aga", "kuid", "vaid", "et", "sest", "kui", "kes",
                    "mis", "või"})


@dataclass(frozen=True)
class NominativeObject:
    """A nimetav phrase where the verb's object stands: `words` are
    (surface, lemma, part of speech), `negated` when an `ei`/`ära` governs it."""
    text: str
    words: tuple[tuple[str, str, str], ...]
    verb: str
    negated: bool
    start: int
    end: int


def _verb_only(token: Token) -> bool:
    """Every reading of the word is a verb: *teate* is also the genitive of
    *teade* (*Teate pikkus*), and *palun* is also the word "please"."""
    if token.text.casefold() == "palun":
        return False
    found = _vm().analyze([token.text], disambiguate=False, guess=False, propername=False)
    readings = [o for item in found for o in item.get("analysis") or []]
    return bool(readings) and all(o.get("partofspeech") == "V" for o in readings)


def _nominative_only(token: Token) -> bool:
    """Every reading of this word as this lemma is the nominative singular."""
    forms = {f for lemma, f in _readings(token.text) if lemma == token.lemma}
    return forms == {"sg n"}


def _clauses_of(tokens: list[Token]) -> list[list[Token]]:
    out: list[list[Token]] = [[]]
    for t in tokens:
        if t.pos == "Z" or t.text.casefold() in _JOINS:
            out.append([])
        else:
            out[-1].append(t)
    return [c for c in out if c]


def _negated(clause: list[Token], at: int) -> bool | None:
    """True when the verb at `at` is negated with a 1st/2nd-person subject (`ma
    ei joo`, `ära joo`); False when not negated; None when negated otherwise."""
    before = clause[at - 1] if at else None
    if before is None or before.pos != "V" or not before.form.startswith("neg"):
        return False
    if before.lemma == "ära":
        return True
    return True if any(t.text.casefold() in _SUBJECT_PRONOUNS
                       for t in clause[:at - 1]) else None


def _not_an_object(tokens: list[Token], at: int, clause: list[Token]) -> bool:
    """What follows the noun shows it is no object: a quantity before a partitive
    (*raasike juttu*), a title before a name (*professor Tamme*), a subject
    coordinated with a pronoun (*vaatasime vend ja mina filmi*), or a finite verb
    in the same clause (*arvan eesti keel on raske*, a comma left out).
    """
    after = tokens[at + 1:at + 3]
    # A capital mid-sentence is a name, whatever Vabamorf reads (*Kaske*: *kask*).
    if after and (after[0].is_partitive or after[0].pos == "H"
                  or after[0].text[:1].isupper()):
        return True
    if (len(after) == 2 and after[0].text.casefold() in ("ja", "ning")
            and after[1].text.casefold() in _SUBJECT_PRONOUNS):
        return True
    rest = clause[clause.index(tokens[at]) + 1:]
    return any(t.pos == "V" and t.form not in _NONFINITE for t in rest)


def nominative_objects(text: str, takes_object) -> list[NominativeObject]:
    """Nimetav singular phrases standing as the object of a verb that takes one.

    `takes_object(lemmas)` returns the verbs, of those given, that EKI's
    dictionaries say take an object. Claimed only where the morphology settles
    it: the phrase follows the verb directly, every word reads only as a
    nimetav singular, its head is a common noun and not a noun of time, and the
    verb is a 1st/2nd-person indicative (`loen raamat`) or negated with a
    1st/2nd-person subject (`ma ei joo kohv`, `ära joo kohv`), and nothing
    after the noun shows it to be something else (`_not_an_object`).
    """
    tokens = analyze(text)
    position = {id(t): n for n, t in enumerate(tokens)}
    verbs = {t.lemma for t in tokens if t.pos == "V"}
    allowed = set(takes_object(sorted(verbs))) - _PREDICATIVE if verbs else set()
    found: list[NominativeObject] = []
    for clause in _clauses_of(tokens):
        for at, verb in enumerate(clause):
            if verb.pos != "V" or verb.lemma not in allowed:
                continue
            # After `ei`/`ära` the word is the verb (*loe* is also a noun).
            negated = _negated(clause, at)
            if negated is None or (not negated and (verb.form not in _PERSONAL
                                                    or not _verb_only(verb))):
                continue
            phrase: list[Token] = []
            for t in clause[at + 1:]:
                if t.pos == "G" or (t.pos == "A" and _nominative_only(t)):
                    phrase.append(t)
                    continue
                if (t.pos == "S" and _nominative_only(t) and t.lemma not in _TIME
                        and not _not_an_object(tokens, position[id(t)], clause)):
                    phrase.append(t)
                    found.append(NominativeObject(
                        text[phrase[0].start:t.end],
                        tuple((w.text, w.lemma, w.pos) for w in phrase),
                        verb.text, bool(negated), phrase[0].start, t.end))
                break
    return found

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
