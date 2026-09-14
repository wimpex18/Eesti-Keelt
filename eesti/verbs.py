"""Irregular verb stems — the `verb-form` gap.

The naive form is the real error: strip `-ma` from `minema` and add `-n` to get
`minen`, where Estonian says `lähen`.

  naive   lemma minus -ma, plus the ending   ->  what the learner will guess
  actual  Vabamorf synthesis                 ->  what Estonian does

Only verbs where the two differ are drilled.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from functools import lru_cache

from estnltk.vabamorf.morf import synthesize

# Vabamorf tag -> (how a naive learner forms it, human-readable Estonian name).
# The naive rule is deliberately the simplest one a beginner is taught.
FORMS: dict[str, tuple[str, str]] = {
    "n": ("n", "olevik, mina"),          # present 1sg      : mine+n  -> lähen
    "d": ("d", "olevik, sina"),          # present 2sg
    "b": ("b", "olevik, tema"),          # present 3sg
    "sin": ("sin", "minevik, mina"),     # past 1sg         : mine+sin -> läksin
    "s": ("s", "minevik, tema"),         # past 3sg
    "nud": ("nud", "mineviku kesksõna"), # past participle  : mine+nud -> läinud
    "da": ("da", "da-infinitiiv"),       # da-infinitive    : mine+da  -> minna
    "ks": ("ks", "tingiv kõneviis"),     # conditional
}


@dataclass(frozen=True)
class VerbForm:
    lemma: str          # ma-infinitive, e.g. "minema"
    tag: str            # Vabamorf tag
    name: str           # Estonian name of the form
    actual: str         # the correct form
    naive: str          # what stripping -ma and adding the ending gives
    level: str | None

    @property
    def is_irregular(self) -> bool:
        return self.actual.lower() != self.naive.lower()


def naive_form(lemma: str, ending: str) -> str:
    """The form a learner builds from the citation form by the simplest rule."""
    stem = lemma[:-2] if lemma.endswith("ma") else lemma
    return stem + ending


@lru_cache(maxsize=4096)
def forms_for(lemma: str) -> tuple[VerbForm, ...]:
    """Every drillable form of one verb, with its naive counterpart."""
    out = []
    for tag, (ending, name) in FORMS.items():
        produced = synthesize(lemma, tag) or []
        if not produced:
            continue
        out.append(
            VerbForm(
                lemma=lemma,
                tag=tag,
                name=name,
                actual=produced[0],
                naive=naive_form(lemma, ending),
                level=None,
            )
        )
    return tuple(out)


def irregular_verbs(
    conn: sqlite3.Connection,
    levels: tuple[str, ...] = ("A1", "A2", "B1"),
    limit: int = 300,
) -> list[VerbForm]:
    """Level-appropriate verbs whose naive forms are wrong, most frequent first (the
    commonest verbs are also the most irregular). The verb pool comes from
    `wordlist.verbs_at_level`, shared with `conjugation.py`.
    """
    from .wordlist import verbs_at_level

    rows = verbs_at_level(conn, levels, limit)

    out: list[VerbForm] = []
    for word, level in rows:
        for form in forms_for(word):
            if form.is_irregular:
                out.append(
                    VerbForm(form.lemma, form.tag, form.name, form.actual,
                             form.naive, level)
                )
    return out
