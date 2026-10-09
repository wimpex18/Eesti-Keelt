"""The shape of a dialogue or reading text, as a model must write it (ADR-0009, step 1).

A draft is JSON. Pydantic validates it here, and the same models give the JSON
Schema a drafting model is held to (`json_schema()`, `cli material schema`), so
the shape the model writes and the shape the gates read cannot drift apart.

Only *shape* is decided here. Whether a form is Estonian, a lemma within the
stage, an answer the text's own words or a gap one right answer is
`eesti/material/gates.py`'s, and a passing shape proves none of it.

Two kinds:

- **dialoog** — `speakers` (an id, a name, a role in Russian) and `turns`, each
  turn one speaker's line;
- **tekst** — `paragraphs`.

Both carry `questions` (a question and the span of the text that answers it),
optional `gaps` (one word of the text, named by its lemma and Vabamorf form, to
be written back), the off-list words with their Russian gloss (`off_list`, at
most `MAX_OFF_LIST`), any `names` the text uses, and who wrote it (`authoring`).
`checks` is written by the pipeline, never by the author.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

#: Bumped when the shape changes in a way old files do not meet.
SCHEMA_VERSION = 1

#: "At most 3 glossed exceptions" (ADR-0009): words beyond the stage's EKI level.
MAX_OFF_LIST = 3

#: How long each kind is (`qa/opus-sessions.md`, S2): a dialogue of 6–10 turns,
#: a text of 80–150 words. Wider than that is a different exercise.
TURNS = (6, 10)
TEXT_WORDS = (80, 150)

_SLUG = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
_ID = r"^[a-z0-9]{1,12}$"


class _Strict(BaseModel):
    # An unknown key is a model's invention or a typo; either way it is refused,
    # because a misspelt `anwser` would otherwise pass as "no answer".
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Speaker(_Strict):
    id: str = Field(pattern=_ID)
    name: str = Field(min_length=1, max_length=40)
    role_ru: str = Field(default="", max_length=80)


class Turn(_Strict):
    speaker: str = Field(pattern=_ID)
    text: str = Field(min_length=1, max_length=400)


class Question(_Strict):
    id: str = Field(pattern=_ID)
    question: str = Field(min_length=3, max_length=200)
    #: The text's own words, verbatim; the gates refuse anything else.
    answer: str = Field(min_length=1, max_length=120)


class Gap(_Strict):
    """One word of the text, to be written from its lemma and named form."""

    id: str = Field(pattern=_ID)
    #: Where the word is: a turn index (dialoog) or a paragraph index (tekst).
    at: int = Field(ge=0)
    word: str = Field(min_length=1, max_length=40)
    lemma: str = Field(min_length=1, max_length=40)
    #: A Vabamorf form tag (`sg p`, `b`), one `gates.GAP_FORMS` names.
    form: str = Field(min_length=1, max_length=12)


class OffList(_Strict):
    lemma: str = Field(min_length=1, max_length=40)
    gloss_ru: str = Field(min_length=1, max_length=80)


class Authoring(_Strict):
    #: The model that wrote the draft (`claude-opus-5-5`).
    engine: str = Field(min_length=1, max_length=60)
    #: The prompt's own version, so a file says which instructions made it.
    prompt_version: str = Field(min_length=1, max_length=40)


class Material(_Strict):
    schema_version: Literal[1] = SCHEMA_VERSION
    kind: Literal["dialoog", "tekst"]
    #: A `units.UNITS` id (`kohvik`).
    unit: str = Field(pattern=_SLUG)
    slug: str = Field(pattern=_SLUG, max_length=40)
    title: str = Field(min_length=1, max_length=80)
    #: The HARNO topic it serves, as `units.HARNO_A2`/`HARNO_B1` write it.
    harno: str = Field(default="", max_length=80)
    speakers: list[Speaker] = Field(default_factory=list, max_length=4)
    turns: list[Turn] = Field(default_factory=list)
    paragraphs: list[str] = Field(default_factory=list, max_length=8)
    #: Proper names the text uses; Vabamorf need not know them.
    names: list[str] = Field(default_factory=list, max_length=8)
    off_list: list[OffList] = Field(default_factory=list, max_length=MAX_OFF_LIST)
    questions: list[Question] = Field(min_length=1, max_length=10)
    gaps: list[Gap] = Field(default_factory=list, max_length=10)
    authoring: Authoring
    #: Written by the pipeline (`blind`), never by the author.
    checks: dict | None = None

    @field_validator("paragraphs")
    @classmethod
    def _no_empty_paragraph(cls, value: list[str]) -> list[str]:
        if any(not p.strip() for p in value):
            raise ValueError("an empty paragraph")
        return [p.strip() for p in value]

    @model_validator(mode="after")
    def _kind_fits(self) -> "Material":
        if self.kind == "dialoog":
            if self.paragraphs:
                raise ValueError("a dialoog has turns, not paragraphs")
            if not TURNS[0] <= len(self.turns) <= TURNS[1]:
                raise ValueError(f"a dialoog has {TURNS[0]}–{TURNS[1]} turns")
            ids = [s.id for s in self.speakers]
            if len(ids) < 2 or len(set(ids)) != len(ids):
                raise ValueError("a dialoog needs two or more distinct speakers")
            if any(t.speaker not in ids for t in self.turns):
                raise ValueError("a turn names a speaker the dialoog does not list")
        else:
            if self.turns or self.speakers:
                raise ValueError("a tekst has paragraphs, not turns or speakers")
            words = sum(len(p.split()) for p in self.paragraphs)
            if not TEXT_WORDS[0] <= words <= TEXT_WORDS[1]:
                raise ValueError(f"a tekst has {TEXT_WORDS[0]}–{TEXT_WORDS[1]} words")
        segments = len(self.turns) if self.kind == "dialoog" else len(self.paragraphs)
        if any(g.at >= segments for g in self.gaps):
            raise ValueError("a gap points past the last turn or paragraph")
        item_ids = [q.id for q in self.questions] + [g.id for g in self.gaps]
        if len(set(item_ids)) != len(item_ids):
            raise ValueError("question and gap ids must be distinct")
        return self

    # ------------------------------------------------------------------
    # What the learner reads
    # ------------------------------------------------------------------

    def segments(self) -> list[str]:
        """The turns as shown (`Mari: Tere!`), or the paragraphs."""
        if self.kind == "tekst":
            return list(self.paragraphs)
        names = {s.id: s.name for s in self.speakers}
        return [f"{names[t.speaker]}: {t.text}" for t in self.turns]

    def lines(self) -> list[str]:
        """What each turn or paragraph says, without the speaker's name."""
        return [t.text for t in self.turns] if self.kind == "dialoog" else list(self.paragraphs)

    def body(self) -> str:
        """The whole text as shown. Answers must occur in *this* once, names included."""
        return "\n".join(self.segments())

    def all_names(self) -> list[str]:
        return list(dict.fromkeys([s.name for s in self.speakers] + self.names))

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    def content(self) -> dict:
        """Everything but the pipeline's own stamp, in a stable order."""
        return self.model_dump(mode="json", exclude={"checks"})

    def sha8(self) -> str:
        """The content's hash: a changed word, key or label is a new material."""
        canonical = json.dumps(self.content(), ensure_ascii=False, sort_keys=True,
                               separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:8]

    def ident(self) -> str:
        """`mat:<unit>:<slug>@<sha8>`, the id content.db and the evidence log use."""
        return f"mat:{self.unit}:{self.slug}@{self.sha8()}"


def json_schema() -> dict:
    """The JSON Schema a drafting model's structured output is held to.

    `checks` is left out: a model that writes its own verdict has not been checked.
    """
    schema = Material.model_json_schema()
    schema["properties"].pop("checks", None)
    return schema


def load(path: Path | str) -> Material:
    """Read and validate one file. Raises `pydantic.ValidationError` or `ValueError`."""
    return Material.model_validate_json(Path(path).read_text(encoding="utf-8"))


def dump(material: Material) -> str:
    """The file as committed: indented, Estonian unescaped, keys in schema order."""
    return json.dumps(material.model_dump(mode="json", exclude_none=True),
                      ensure_ascii=False, indent=2) + "\n"
