"""English and Ukrainian glosses a model drafts, and a second model checks blind.

Where no source the app has gives a word's English or Ukrainian, the dictionary
may show a model's draft — labelled as one, with its engine — but only a draft
that survived these steps, in order (ADR-0009, "Material without a human
reviewer"):

1. **A source to translate from.** Only words EKI's Estonian–Russian
   dictionary translates are drafted, and the draft is asked for the senses
   EKI's Russian shows (with EKI's learner definition where PSV has one): the
   model translates EKI's sense, it does not decide what the word means.
2. **Claude Opus 5.5 drafts**, through the Message Batches API with one cached
   system prompt (`DRAFT_SYSTEM`, prompt `DRAFT_PROMPT`).
3. **Code gates the draft** (`dictionary.gate`): English in Latin letters,
   Ukrainian in its own alphabet with none of Russian's own letters (ы, э, ъ,
   ё), at most three short equivalents. A word Ukrainian shares with Russian
   (*зуб*, *сад*) stays. The first equivalent is the main sense: if it fails,
   the draft is refused whole; a later one that fails is dropped.
4. **Claude Haiku 5.5 translates it back, blind** (`BACK_SYSTEM`,
   `BACK_SYSTEM_UK`): it is shown only the English or the Ukrainian and the
   part of speech, never the Estonian word, its Russian or the other
   language, and names the Estonian headword; for Ukrainian it also lists the
   given words that are not standard Ukrainian (Russian or surzhyk). **Code
   decides**: a flagged word is dropped, a flagged main sense refuses the
   draft whole, and a draft whose back-translation does not name the word
   again (`dictionary.agrees`, Vabamorf reading each candidate) is refused.
5. **Stored with its evidence**: engine, prompt version, checker, its prompt
   version, its Estonian, the gated draft and the words it flagged, in
   `content/dictionary/glosses.jsonl`; refusals
   and why in `rejected.jsonl`; every batch and what it cost in
   `batches.jsonl`. The image imports the kept file into the words database
   (`dictionary.import_glosses`), re-checking every line.

The word set is bounded: EKI's A1 list and the words the course units teach
(`themes.THEMES`, `units.FIRST_WORDS`). Run with `cli dictionary glosses`.
"""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from . import dictionary

ROOT = Path(__file__).resolve().parent.parent / "content" / "dictionary"

#: The drafting model, its effort, and its prompt version.
MODEL = "claude-opus-5-5"
EFFORT = "medium"
DRAFT_PROMPT = "s9-gloss-1"
#: The checker: a different model, never the drafting one (`dictionary.check_record`).
CHECKER = "claude-haiku-5-5"
CHECK_EFFORT = "medium"
CHECK_PROMPT = "s9-back-1"
#: Ukrainian's check also asks which words are not standard Ukrainian.
CHECK_PROMPT_UK = "s9-back-2"
CHECK_PROMPTS = {"en": CHECK_PROMPT, "uk": CHECK_PROMPT_UK}

#: Words per drafting request, items per back-translation request.
PER_DRAFT = 20
PER_CHECK = 30
#: Room for the answer and adaptive thinking.
DRAFT_TOKENS = 16000
CHECK_TOKENS = 8000

#: Dollars per million tokens through the Batches API, half the interactive
#: price (ADR-0008: Opus 5.5 $4 / $20, Haiku 5.5 $0.10 / $0.50).
PRICE = {
    MODEL: {"input": 2.0, "output": 10.0, "cache_write": 2.5, "cache_read": 0.2},
    CHECKER: {"input": 0.05, "output": 0.25, "cache_write": 0.0625, "cache_read": 0.005},
}

#: Parts of speech as the prompts name them.
POS_EN = {"s": "noun", "v": "verb", "adj": "adjective", "adv": "adverb", "num": "numeral",
          "pron": "pronoun", "konj": "conjunction", "conj": "conjunction",
          "postp": "postposition", "prep": "preposition", "interj": "interjection",
          "prop": "proper noun"}

LANGUAGE = {"en": "English", "uk": "Ukrainian"}

DRAFT_SYSTEM = """You write the English and Ukrainian equivalents of Estonian headwords for a learner's dictionary.

For each headword you are given its part of speech, the Russian equivalents from the Estonian Language Institute's Estonian-Russian dictionary (EKI), main sense first, and sometimes EKI's learner definition in Estonian.

For every headword give:
- "en": one to three English equivalents of the senses the Russian shows, main sense first;
- "uk": one to three Ukrainian equivalents of the same senses, main sense first.

Rules:
- Translate the Estonian word in the senses EKI's Russian shows. Do not add senses the Russian does not show, and never translate another meaning the Russian word has in Russian.
- Give dictionary forms: nouns in the singular (English without an article; Ukrainian in the nominative), verbs as the bare infinitive (English without "to"; Ukrainian in -ти), adjectives in the masculine singular.
- Each equivalent is a word or a short phrase of at most four words: no explanations, brackets, examples or grammar notes.
- Ukrainian must be Ukrainian, not Russian: Ukrainian spelling and vocabulary (і, ї, є, ґ, the apostrophe), never the letters ы, э, ъ or ё.
- Lower case, except words that are always capitalised (English "I", names).
- If you are not sure of an equivalent, give fewer rather than guess.

Reply with JSON only: {"words": [{"id": "...", "en": [...], "uk": [...]}]}, one object for every id you were given."""

BACK_SYSTEM = """You name Estonian words.

You are given dictionary equivalents of Estonian headwords in English or in Ukrainian, each with its part of speech. For each item, name the Estonian headword it translates: one to three candidates, the most likely first, each in the Estonian dictionary form (nouns and adjectives in the nominative singular, verbs in the ma-infinitive, such as lugema).

Reply with JSON only: {"items": [{"id": "...", "et": ["...", "..."]}]}, one object for every id you were given."""

BACK_SYSTEM_UK = """You name Estonian words, and you check Ukrainian.

You are given dictionary equivalents of Estonian headwords in Ukrainian, each with its part of speech; one item's words are separated by semicolons. For each item give:
- "et": the Estonian headword it translates: one to three candidates, the most likely first, each in the Estonian dictionary form (nouns and adjectives in the nominative singular, verbs in the ma-infinitive, such as lugema);
- "not_ukrainian": every given word or phrase that is not standard Ukrainian, copied exactly as given: a Russian word, surzhyk, or a Russian spelling. A word Ukrainian shares with Russian (зуб, сад, вода) is standard Ukrainian and is not listed. An empty list when every word is standard Ukrainian.

Reply with JSON only: {"items": [{"id": "...", "et": ["...", "..."], "not_ukrainian": []}]}, one object for every id you were given."""

DRAFT_SCHEMA = {
    "type": "object",
    "properties": {"words": {"type": "array", "items": {
        "type": "object",
        "properties": {"id": {"type": "string"},
                       "en": {"type": "array", "items": {"type": "string"}},
                       "uk": {"type": "array", "items": {"type": "string"}}},
        "required": ["id", "en", "uk"], "additionalProperties": False}}},
    "required": ["words"], "additionalProperties": False,
}

BACK_SCHEMA = {
    "type": "object",
    "properties": {"items": {"type": "array", "items": {
        "type": "object",
        "properties": {"id": {"type": "string"},
                       "et": {"type": "array", "items": {"type": "string"}}},
        "required": ["id", "et"], "additionalProperties": False}}},
    "required": ["items"], "additionalProperties": False,
}


BACK_SCHEMA_UK = {
    "type": "object",
    "properties": {"items": {"type": "array", "items": {
        "type": "object",
        "properties": {"id": {"type": "string"},
                       "et": {"type": "array", "items": {"type": "string"}},
                       "not_ukrainian": {"type": "array", "items": {"type": "string"}}},
        "required": ["id", "et", "not_ukrainian"], "additionalProperties": False}}},
    "required": ["items"], "additionalProperties": False,
}

#: Each language's checker prompt and answer shape.
CHECKS = {"en": (BACK_SYSTEM, BACK_SCHEMA), "uk": (BACK_SYSTEM_UK, BACK_SCHEMA_UK)}


@dataclass(frozen=True)
class Word:
    """A headword to draft for, with the source its draft translates."""

    lemma: str
    pos: str
    russian: tuple[str, ...]
    definition: str | None = None


@dataclass
class Draft:
    """One gated draft in one language, waiting for its back-translation."""

    lemma: str
    lang: str
    gloss: list[str]
    anchor: list[str]
    pos: str
    batch: str = ""
    back: list[str] = field(default_factory=list)
    #: The gated draft the checker was shown, and the words it flagged.
    draft: list[str] = field(default_factory=list)
    flagged: list[str] = field(default_factory=list)

    def record(self, **extra) -> dict:
        found = {"lemma": self.lemma, "lang": self.lang, "gloss": self.gloss,
                 "anchor": self.anchor, "pos": self.pos, "engine": MODEL,
                 "prompt": DRAFT_PROMPT, "effort": EFFORT, "checker": CHECKER,
                 "check_prompt": CHECK_PROMPTS[self.lang], "back": self.back,
                 "batch": self.batch, "draft": self.draft or self.gloss}
        if self.lang == "uk":
            found["flagged"] = self.flagged
        return {**found, **extra}


# ---------------------------------------------------------------------------
# Which words
# ---------------------------------------------------------------------------

def wanted() -> list[str]:
    """The bounded set, before filtering: the words the course units teach and
    EKI's A1 list (read from the words database by `candidates`)."""
    from .themes import THEMES
    from .units import FIRST_WORDS

    out = [w for _, group in FIRST_WORDS for w in group]
    out += [w for t in THEMES for w in (*t.nouns, *t.verbs)]
    return list(dict.fromkeys(out))


def _done(root: Path) -> set[tuple[str, str]]:
    """(lemma, language) already kept or refused: never drafted twice."""
    out: set[tuple[str, str]] = set()
    for name in ("glosses.jsonl", "rejected.jsonl"):
        path = root / name
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    record = json.loads(line)
                    out.add((record["lemma"], record["lang"]))
    return out


def candidates(words: sqlite3.Connection, root: Path | None = None,
               limit: int | None = None) -> list[Word]:
    """Single words of the bounded set that EKI EVS translates and that have
    no kept or refused draft yet, in the word list's frequency order."""
    from . import evs
    from .psv import lookup as psv

    root = root or ROOT
    done = _done(root)
    try:
        a1 = [r[0] for r in words.execute(
            "SELECT o.word FROM official_levels o LEFT JOIN words w ON w.word = o.word"
            " WHERE o.level = 'A1' ORDER BY (w.freq_rank IS NULL OR w.freq_rank = 0),"
            " w.freq_rank, o.word")]
    except sqlite3.Error:
        a1 = []
    out: list[Word] = []
    for lemma in dict.fromkeys(wanted() + a1):
        if " " in lemma or all((lemma, lang) in done for lang in dictionary.GLOSS_LANGS):
            continue
        russian = evs.russian(words, lemma)
        if not russian:
            continue
        row = dictionary._word_row(words, lemma)
        codes = dictionary._pos_codes(row["pos"] if row else None) \
            or dictionary._pos_codes(dictionary._evs_pos(words, lemma))
        simple = psv(words, lemma)
        out.append(Word(lemma, codes[0] if codes else "", tuple(russian[:5]),
                        simple.definition if simple else None))
        if limit and len(out) >= limit:
            break
    return out


# ---------------------------------------------------------------------------
# Requests
# ---------------------------------------------------------------------------

def _chunks(items: list, size: int) -> list[list]:
    return [items[i:i + size] for i in range(0, len(items), size)]


def draft_text(group: list[Word]) -> str:
    """The user turn for one drafting request: ids, never more than the source."""
    lines = []
    for n, w in enumerate(group, 1):
        lines.append(f"id: w{n}\nheadword: {w.lemma}\npart of speech: {POS_EN.get(w.pos, w.pos or 'unknown')}"
                     f"\nRussian (EKI): {'; '.join(w.russian)}"
                     + (f"\nEstonian definition (EKI): {w.definition}" if w.definition else ""))
    return "\n\n".join(lines)


def _request(custom_id: str, model: str, effort: str, system: str, text: str,
             schema: dict, tokens: int) -> dict:
    return {"custom_id": custom_id, "params": {
        "model": model, "max_tokens": tokens,
        "system": [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        "messages": [{"role": "user", "content": text}],
        "output_config": {"effort": effort, "format": {"type": "json_schema", "schema": schema}},
    }}


def draft_requests(words: list[Word]) -> tuple[list[dict], dict[str, list[Word]]]:
    """The drafting batch, and which words each request carries."""
    groups = {f"d{n}": group for n, group in enumerate(_chunks(words, PER_DRAFT))}
    return ([_request(cid, MODEL, EFFORT, DRAFT_SYSTEM, draft_text(group), DRAFT_SCHEMA,
                      DRAFT_TOKENS) for cid, group in groups.items()], groups)


def back_text(group: list[Draft]) -> str:
    """The checker's user turn: the gloss and the part of speech, nothing else."""
    lang = LANGUAGE[group[0].lang]
    return "\n\n".join(
        f"id: i{n}\npart of speech: {POS_EN.get(d.pos, d.pos or 'unknown')}\n{lang}: {'; '.join(d.gloss)}"
        for n, d in enumerate(group, 1))


def back_requests(drafts: list[Draft]) -> tuple[list[dict], dict[str, list[Draft]]]:
    """The back-translation batch, one language per request."""
    groups: dict[str, list[Draft]] = {}
    for lang in dictionary.GLOSS_LANGS:
        for n, group in enumerate(_chunks([d for d in drafts if d.lang == lang], PER_CHECK)):
            groups[f"b{lang}{n}"] = group
    requests = []
    for cid, group in groups.items():
        system, schema = CHECKS[group[0].lang]
        requests.append(_request(cid, CHECKER, CHECK_EFFORT, system, back_text(group), schema,
                                 CHECK_TOKENS))
    return requests, groups


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------

def _json(text: str | None) -> dict | None:
    if not text:
        return None
    try:
        found = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.S)
        if not match:
            return None
        try:
            found = json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
    return found if isinstance(found, dict) else None


def collect(client, batch_id: str) -> tuple[dict[str, str | None], dict[str, int]]:
    """custom_id → the reply's text (None where it failed, was refused or cut
    off), and the batch's token use."""
    texts: dict[str, str | None] = {}
    usage = {"input": 0, "output": 0, "cache_write": 0, "cache_read": 0}
    for result in client.messages.batches.results(batch_id):
        outcome = result.result
        if outcome.type != "succeeded":
            texts[result.custom_id] = None
            continue
        message = outcome.message
        used = getattr(message, "usage", None)
        for key, attr in (("input", "input_tokens"), ("output", "output_tokens"),
                          ("cache_write", "cache_creation_input_tokens"),
                          ("cache_read", "cache_read_input_tokens")):
            usage[key] += getattr(used, attr, 0) or 0
        if getattr(message, "stop_reason", None) in ("refusal", "max_tokens"):
            texts[result.custom_id] = None
            continue
        texts[result.custom_id] = "".join(getattr(b, "text", "") for b in message.content
                                          if getattr(b, "type", "") == "text")
    return texts, usage


def cost(model: str, usage: dict[str, int]) -> float:
    """Dollars for a batch's token use."""
    price = PRICE[model]
    return round(sum(usage.get(k, 0) * price[k] for k in price) / 1_000_000, 4)


def gate_drafts(texts: dict[str, str | None], groups: dict[str, list[Word]],
                batch: str = "", done: set[tuple[str, str]] = frozenset()
                ) -> tuple[list[Draft], list[dict]]:
    """Gated drafts, and the refusals with why. A word the reply leaves out is
    refused: an unconfirmed draft is an unchecked one. A language `done`
    already has a kept or refused record and is not judged twice."""
    drafts: list[Draft] = []
    refused: list[dict] = []
    for cid, group in groups.items():
        reply = _json(texts.get(cid))
        by_id = {}
        for item in (reply or {}).get("words") or []:
            if isinstance(item, dict) and isinstance(item.get("id"), str):
                by_id[item["id"]] = item
        for n, word in enumerate(group, 1):
            item = by_id.get(f"w{n}")
            for lang in dictionary.GLOSS_LANGS:
                if (word.lemma, lang) in done:
                    continue
                base = Draft(word.lemma, lang, [], list(word.russian), word.pos, batch)
                if item is None:
                    refused.append(base.record(stage="draft", why="no draft came back"))
                    continue
                kept, why = dictionary.gate(lang, item.get(lang))
                if why:
                    base.gloss = [str(x) for x in item.get(lang) or []][:5]
                    refused.append(base.record(stage="gate", why=why))
                    continue
                base.gloss, base.draft = kept, list(kept)
                drafts.append(base)
    return drafts, refused


def judge(texts: dict[str, str | None], groups: dict[str, list[Draft]],
          check_batch: str = "") -> tuple[list[dict], list[dict]]:
    """Kept records and refusals, decided by code from the blind checker's
    answer: a word it flags as not standard Ukrainian is dropped, a flagged
    main sense refuses the draft whole, and the back-translation must name the
    word again."""
    on = datetime.now(timezone.utc).date().isoformat()
    kept: list[dict] = []
    refused: list[dict] = []
    for cid, group in groups.items():
        reply = _json(texts.get(cid))
        by_id = {i["id"]: i for i in (reply or {}).get("items") or []
                 if isinstance(i, dict) and isinstance(i.get("id"), str)}
        for n, draft in enumerate(group, 1):
            item = by_id.get(f"i{n}")
            back = [str(x) for x in (item or {}).get("et") or [] if isinstance(x, str)][:3]
            draft.back, draft.draft = back, list(draft.draft or draft.gloss)
            said = {str(x).strip().casefold() for x in (item or {}).get("not_ukrainian") or []}
            draft.flagged = [w for w in draft.draft if w.casefold() in said] \
                if draft.lang == "uk" else []
            draft.gloss = [w for w in draft.draft if w not in draft.flagged]
            meta = {"check_batch": check_batch, "drafted": on}
            if item is None:
                refused.append(draft.record(stage="back", why="no back-translation came back", **meta))
            elif draft.draft[0] in draft.flagged:
                refused.append(draft.record(
                    stage="back", why=f"main sense not standard Ukrainian: {draft.draft[0]}", **meta))
            elif not dictionary.agrees(draft.lemma, back):
                refused.append(draft.record(
                    stage="back", why=f"back-translated as {', '.join(back) or 'nothing'}", **meta))
            else:
                kept.append(draft.record(**meta))
    return kept, refused


# ---------------------------------------------------------------------------
# Files
# ---------------------------------------------------------------------------

def append(path: Path, records: list[dict]) -> None:
    """Add records to a JSON-lines file, the whole file kept sorted by lemma and
    language so a later run's diff shows only what it added."""
    lines = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines()
             if l.strip()] if path.exists() else []
    lines += records
    lines.sort(key=lambda r: (r["lemma"], r["lang"]))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in lines),
                    encoding="utf-8")


def log_batch(root: Path, **entry) -> None:
    root.mkdir(parents=True, exist_ok=True)
    with (root / "batches.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"on": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                             **entry}, ensure_ascii=False) + "\n")


def save_drafts(root: Path, drafts: list[Draft], batch: str) -> Path:
    """The gated drafts between the two batches (git-ignored work in progress)."""
    path = root / "drafts" / f"{batch}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(d.__dict__, ensure_ascii=False) + "\n" for d in drafts),
                    encoding="utf-8")
    return path


def load_drafts(path: Path) -> list[Draft]:
    return [Draft(**json.loads(l)) for l in path.read_text(encoding="utf-8").splitlines()
            if l.strip()]
