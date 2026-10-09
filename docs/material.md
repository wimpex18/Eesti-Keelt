# Material written with a model

Unit dialogues and reading texts are drafted by a model and kept only when code
and a second model's blind check accept them (ADR-0009, "Material without a
human reviewer"; ADR-0004). This is the pipeline, `eesti/material/`.

```bash
python -m eesti.cli material schema                  # the JSON Schema a draft must meet
python -m eesti.cli material check DRAFT.json...     # the deterministic gates
python -m eesti.cli material blind DRAFT.json...     # Haiku 5.5, blind, via the Batches API
python -m eesti.cli material build                   # content/material/checked/ → content.db
python -m eesti.cli material stats                   # answers, reports, retired items
```

`check` and `build` need the word list with EKI's levels (`cli build`,
`cli import-levels`). `blind` needs `ANTHROPIC_API_KEY` in the git-ignored `.env`.

## 1. The draft

One JSON file per dialogue or text (`eesti/material/schema.py`; unknown keys
are refused):

| Field | What it holds |
|---|---|
| `kind` | `dialoog` (6–10 `turns` by 2–4 `speakers`) or `tekst` (`paragraphs`, 80–150 words) |
| `unit`, `slug`, `title`, `harno` | the `units.UNITS` id, a file name, the title, the HARNO topic |
| `speakers` | `id`, `name`, `role_ru` |
| `turns` | `speaker` (an id), `text` |
| `names` | other proper names the text uses; Vabamorf need not know them |
| `off_list` | at most 3 `{lemma, gloss_ru}`: words beyond the stage's EKI level |
| `questions` | `id`, `question`, `answer` — the answer is the text's own words |
| `gaps` | `id`, `at` (turn or paragraph index), `word`, `lemma`, `form` (a Vabamorf tag) |
| `authoring` | `engine` and `prompt_version` |

`checks` is written by the pipeline, never by an author; a draft that carries one
without a blind check is refused.

## 2. The deterministic gates

Run in this order by `cli material check` (`eesti/material/gates.py`). A failure
in the text fails the draft; a question or gap that fails a gate is dropped with
the gate's name; fewer than 3 surviving questions fail the draft.

1. **schema** — the shape above.
2. **vabamorf** — every word of the text, its questions and gaps is a form
   Vabamorf knows with `guess=False`, and its spellchecker accepts it. Declared
   names are exempt.
3. **level** — every content lemma (noun, verb, adjective, adverb) is on EKI's
   A1/A2/B1 list (`official_levels`, never the frequency estimate) at or below
   the unit's stage — Algus and A1: A1; A2: A1–A2; B1: A1–B1 — or declared in
   `off_list`. Any reading Vabamorf allows counts, because its disambiguator
   reads *Ma joon* as the noun "line". A declared word that is unused or already
   on the list fails the draft: its gloss would be a false label.
4. **forms** — every form tag in Vabamorf's disambiguated reading comes from a
   topic introduced by this unit or earlier:

   | Form | Topic |
   |---|---|
   | nominative singular, uninflected words, numerals in digits | none |
   | `sg g`, `sg p` | `pohivormid` |
   | `sg ill/in/el/all/ad/abl`, `adt` | `kohakaanded` |
   | `sg tr/ter/es/ab/kom` | `harvad-kaanded` |
   | any plural | `mitmus` (and the case's topic) |
   | any pronoun form | `asesonad` (the EKI teatmik tables) |
   | comparative, superlative / ordinal / adposition | `vordlusastmed` / `jargarvud` / `kaassonad` |
   | a conjunction other than *ja*, *aga*, *või* | `sidesonad` |
   | `n d b me te vad` | `olevik` |
   | `neg`; `o` and `nud` after *ei*/*ega*; *pole*, *polnud* | `eitus` |
   | `o`, `ge`, `gu`, *ära* | `kaskiv` |
   | `s sin sid sime site` | `lihtminevik` |
   | `ma`, `da` | `verb-form` |
   | `mas mast mata maks des` | `ma-vormid` |
   | `ks …`, `nuks` | `tingiv` |
   | `nud` (not after *ei*) | `taisminevik` |
   | `tud`, `tav`, `v` | `kesksonad` |
   | `takse ti ta …` | `umbisikuline` |
   | `vat`, `tavat` | `kaudne` |

   An unmapped tag is refused. Words inside one of EKI's A1 phrases
   (`eesti/phrases.py`) are exempt: *Tere hommikust!* is taught whole in unit 1.
   A declared name is exempt from Vabamorf's lexicon, not from this gate:
   *Svetlanale* needs `kohakaanded`. The disambiguated reading is judged, so
   *Piima ma ei taha* (read as the short illative) fails at unit 4; reword it.
5. **answers** — the answer occurs exactly once, as whole words, in the text as
   shown (speakers' names included), is 1–8 words, and the question, which ends
   with a question mark and has at least three words, does not contain it
   (`comprehension.verify`).
6. **gaps** — one right answer: the form has a label a learner can be shown
   (`gates.GAP_FORMS`); the word occurs once in its line and Vabamorf reads it
   there as the named lemma and form; Vabamorf generates exactly that word for
   them (a free variant such as *kaht*/*kahte* or a homograph is refused); no
   other form under the same label gives another word (*majja*/*majasse*); and
   the form's topic is introduced.
7. **duplicates** — no question, answer or gap twice.

## 3. The blind check

`cli material blind` gates the drafts, then sends the surviving items to Claude
Haiku 5.5 through the Message Batches API (`eesti/material/blind.py`, prompt
`blind-1`, effort high, structured output): each question **with the text and
without the key**, each question **without the text**, and each gap with its
word blanked and its lemma and form named. Code grades every reply
(`comprehension.grade`):

- a question answered wrongly with the text, or not answered, is dropped;
- a question answered rightly without the text is dropped as guessable;
- a gap filled with another word is dropped.

A gap is not asked without its text: it names its form, so it is answerable
from that cue by design. The gates run again on what is left; a draft that
passes is written to `content/material/checked/<unit>/<slug>.json` with
`checks`: the gate version, the engine, the batch id and the hash of the
content. A batch that has not ended within `--wait` is collected later with
`--batch <id>` and the same drafts.

## 4. Storage and the label

The checked files are committed; the record is the file. `cli material build`
re-runs the gates on each, compares its hash with the stamp, and refuses a file
edited after its checks or one a newer gate refuses — it never trims one. Each
file becomes, in `content.db`:

- an `items` row with id `mat:<unit>:<slug>@<sha8>` under the public source
  `grove-material` (`eesti/licences.py`), skill `lugemine`, labelled
  *написано моделью, проверено Vabamorf и автоматическими проверками* with its
  engine and prompt version, and no key;
- a `material` row with the same id holding the checked document, keys
  included, read only by the server.

Material whose file is gone is removed. A changed word is a new hash and so a
new id; an attempt recorded against the old one keeps its question and key in
the evidence log.

## 5. In the app

| Route | Does |
|---|---|
| `GET /api/material/units/{unit_id}` | the unit's material: turns or paragraphs, questions and gap prompts without keys, off-list glosses, label, engine, prompt version; retired items left out |
| `POST /api/material/answer` | `{material, item, answer}`: code grades against the stored key; recorded as `comprehension` in the learner's log and counted |
| `POST /api/material/report` | *Teata veast*: `{material, item, reason, note}`, reason one of `vale-vastus`, `mitu-vastust`, `viga-tekstis`, `muu`; an empty item is the whole text |

Answers and reports are counted in the owner's `progress.db`, which every scope
counts in and the snapshot carries (`eesti/material/stats.py`). An answer is
kept as a hash of its normalised words, a reporter as a hash of their scope, a
note at most 300 characters. An item is retired, for good, when:

- **its answers split** — 20 or more answers, and one wrong answer given by 30 %
  of them;
- **its answers never vary** — 30 or more answers, all right or all wrong;
- **it is reported** — by two people, or once by the owner.

Only the owner's and learners' answers and reports count: a guest sandbox is a
name anyone can choose. A report on the whole text withdraws the material.

## Limits

- Gaps name their form. A gap decided by context alone (the object's case)
  needs a code-known trigger and is not built yet.
- The forms gate trusts Vabamorf's disambiguator and so refuses some correct
  sentences; the level gate trusts any reading and so accepts a homograph.
- The unit page does not show the material yet; the routes are ready for it.
