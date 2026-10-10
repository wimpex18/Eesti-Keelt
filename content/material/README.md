# Unit dialogues and reading texts

Material for the course's units, written with a model and kept only when code
and a second model's blind check accept it (ADR-0009; the pipeline is
`docs/material.md`). Units 2–10 (the A1 stage) each have one dialogue and one
reading text on the unit's HARNO topic, five questions each:

| # | Unit | Dialoog | Tekst |
|---|---|---|---|
| 2 | `tutvume` | *Uus õpilane* (`kursusel`) | *Mina olen Igor* (`uus-oppija`) |
| 3 | `pere` | *Pere pilt* (`pilt`) | *Minu pere* (`minu-pere`) |
| 4 | `kohvik` | *Kohv ja sai* (`kohvikus`) | *Igori lõuna* (`lounapaus`) |
| 5 | `kodu` | *Uus korter* (`uus-korter`) | *Minu kodu* (`minu-kodu`) |
| 6 | `paev` | *Homme õhtul* (`millal`) | *Olga päev* (`minu-paev`) |
| 7 | `linn` | *Kus on apteek?* (`tee-kusimine`) | *Minu linn* (`minu-linn`) |
| 8 | `meeldib` | *Nädalavahetuse plaan* (`nadalavahetus`) | *Olga vaba aeg* (`vaba-aeg`) |
| 9 | `eile` | *Mida sa eile tegid?* (`puhkepaev`) | *Reis Tartusse* (`reis`) |
| 10 | `poes` | *Turul* (`turul`) | *Olga käis poes* (`poeskaik`) |

| Path | What it is |
|---|---|
| `checked/<unit>/<slug>.json` | Material that passed the gates and the blind check, stamped by `cli material blind`. The record: `cli material build` re-checks each file into `content.db`. |
| `draft.py` | How the drafts were asked for: the system prompt, each unit's brief, the Batches API calls. |
| `log.md` | Every draft the gates or the blind check refused, and why. |
| `rejected/<unit>/<slug>.r<n>.json` | Drafts the gates or `draft.py`'s own checks refused, round `n`. A draft the blind check left short was revised too; its drops are in `log.md`. |
| `batches.jsonl` | Each Batches API call: batch id, drafting or revision, prompt version. |

## How a file was made

1. **Draft.** `draft.py submit` asks Claude Opus 5.5 (`claude-opus-5-5`,
   effort high, adaptive thinking) through the Message Batches API for a
   dialogue and a text per unit, held to the material schema by structured
   output. The system prompt is one cached prefix: the gates in plain words,
   EKI's A1 phrases and situation exchanges, the grammar no unit 2–10 allows,
   and EKI's A1 word list. Each request then names the unit, its situation, its
   word set, and the forms taught by the end of that unit (`gates.introduced`).
2. **Gates.** `draft.py collect` writes each draft and runs `cli material
   check`'s gates on it; what they refuse is logged and kept under `rejected/`.
3. **Revise.** `draft.py revise` sends a refused draft back with the gates'
   and the blind check's findings, verbatim, under prompt `s2-revise-1`; a
   revised file's `prompt_version` names each round (`s2-draft-1+s2-revise-1`).
   Where the session's reader saw a fault no check names (a plan that
   contradicts itself, a question with two answers), the note went with the
   findings, labelled as a reader's, and is recorded in `batches.jsonl`.
4. **Trim.** Drafts ask for seven questions. A first `cli material blind` run
   into a scratch directory shows which of them survive; `draft.py trim
   --blind <its output>` keeps the first five of those. A question the reader
   leaves out (`--drop`, with `--why`) is logged with its reason.
5. **Blind check.** `cli material blind` (Claude Haiku 5.5, Batches API)
   answers each question with and without the text and fills each gap; what it
   gets wrong or guesses is dropped, and what passes is written to `checked/`
   with the pipeline's stamp. Every drop, in either run, is copied into
   `log.md`.

`draft.py` also asks of every draft what the gates do not: no digits in an
answer (`comprehension` compares letters only, so *6 eurot* would match
*5 eurot*), and, for a text, at least five sentence endings that HARNO's B1
reading task 4 can remove into its phrase bank (`harnotasks.phrase_bank`).

Every file names its engine and prompt version (`authoring`); every Estonian
form in it was accepted by Vabamorf, every content word is on EKI's A1 list or
one of at most three glossed exceptions (`off_list`), and every answer key is
the text's own words, checked by code. A model wrote the sentences; none of
them was read by a person before release, so the app labels them as written
with a model.

## Sources

- Situations and phrasing: Sõrmus, E., Pool, R., Kallas, J., Kiisla, O. (2025)
  *Kasulikke väljendeid A1-tasemel eesti keele õppijale* and *… A2-tasemel …*,
  Eesti Keele Instituut, Sõnaveeb, CC BY 4.0
  (<https://sonaveeb.ee/learn#v-pills-kasulikke-valjendeid-a1>, `…-a2`; read
  10 Oct 2026). The exchanges the prompt quotes are in `draft.py`
  (`SITUATIONS`); the dialogues reuse some of them word for word.
- Word level: EKI's A1/A2/B1 word list (`official_levels`, `cli import-levels`).
- Forms: Vabamorf (`estnltk`), through the gates.
