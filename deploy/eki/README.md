# EKI's dictionary downloads, committed

Six files from <https://arhiiv.eki.ee/litsents/>, all CC BY 4.0, committed here
since 2026-09-13 and imported by the `Dockerfile` into `data/eesti.db`. The
learner downloaded them — direct links worked that day, without the ID-card
step recorded on 2026-09-12 — and nothing in this repo fetches from EKI.

| File | What it is | What it turns on |
|---|---|---|
| `A1A2B1.txt` | *Eesti keele tasemete sõnavara* — 4 456 lemmas, A1 740 · A2 1 266 · B1 2 450 | `words.level` is EKI's answer, `words.level_source` says so |
| `psv_EKI_CCBY40.xml.gz` | *Eesti keele põhisõnavara sõnastik* — 4 849 learner-level definitions | the word card's definition and examples |
| `evs_EKI_CCBY40.xml.gz` | *Eesti-vene sõnaraamat* — 60 672 lemmas with Russian | the word card's and the drills' Russian, offline |
| `vsl_EKI_CCBY40.xml.gz` | *Võõrsõnade leksikon* — 30 095 definitions | last-fallback definition |
| `har_EKI_CCBY40.xml.gz` | *Haridussõnastik* — 5 905 terms with Russian | last-fallback Russian |
| `ekss_EKI_CCBY40.xml.gz` | *Eesti keele seletav sõnaraamat* — 117 937 definitions, 96 058 for words in the word list | last-fallback definition |

Counts measured on the real files, 2026-09-13. EKI's terms: process and present
the material any way needed, an app included, provided the attribution stays and
the changes are described. Both live in `eesti/licences.py`, and `/api/sources`
serves them; the word card credits EKI on whatever EKI wrote.

## Where the learner meets it, and in which order

Every source keeps its own table, and none writes another's.

The live dictionary — EKI's Ekilex API when `EKILEX_API_KEY` is set, the Sõnaveeb mirror otherwise — is EKI's database as it is now; every
file here is a snapshot. So the live answer wins wherever it is the same kind of
answer, and the files fill what it leaves empty, answer when it cannot be asked
(offline, over the daily budget, down), and serve every flow that must not wait
on a network. The word card always asks it.

- **Russian** — seed glossary → live dictionary → EVS → HAR, stated once in
  `eesti/meaning.py` and used by every flow that shows a meaning: the word card
  (Lugemine and Sõnavara), the Sõnavara list, the gloss beside a drill, the
  gloss after a graded answer, and the review flashcard made with *Kordamisse*.
  The seed (294 hand-written glosses for the drill words) comes first because
  it names the drilled sense: EVS puts a different first translation on 45 of
  them — `kohus` "долг", not "суд".
- **Estonian definition** — PSV's learner wording first, because it is written
  for someone learning the word; then the live dictionary, VSL, EKSS. When PSV
  answers, the native-level wording (live, else EKSS/VSL) is on the card too,
  folded under *täpsem seletus*: `eesti/api/grammar.py`, `_meaning`.
- **Examples** — PSV's.
- **Rektsioon and muuttüüp** — the live dictionary's, else PSV's rection (872
  articles) and EVS's inflection type (43 886 lemmas; the ones EKI mark unsure
  are left to the live dictionary).
- **CEFR level** — EKI's list over the estimate, everywhere a level is shown or
  filtered (`words.level_source`), as before.

Nothing needs the learner to open a file; the card credits EKI on whatever EKI
wrote, and `Allikad` lists every source with its changes.

## Every file in the download, and what became of it

Measured 2026-09-13, each against what the app already had.

| File | Used? | What was measured |
|---|---|---|
| `A1A2B1.txt`, `psv`, `evs`, `vsl`, `har`, `ekss` `_EKI_CCBY40.xml` | imported, committed (XML gzipped) | above |
| `schema_*.xsd`, `*_tyybid.xsd` | read; they set the import rules | the style labels (`van`, `kõnek`, `hlv`…, HAR's `halb`), the `l="ka"` "also" qualifier, and the headword marks `+`, `\|` and a backslash |
| `marksonad.txt` | not imported | EKSS's headword index: 115 027 of its 138 392 lines are exactly EKSS's lemmas; the other 23 265 are names used inside compounds (`Aafrika`, `Austria`) and affixes, with no definition to show |
| `ekss.html.gz` | not imported | the same 145 882 EKSS articles rendered as HTML |
| `scrabble.txt` | not imported | 136 771 bare word forms for a word game, no meaning attached; 110 548 are already in the word list, and Vabamorf is this app's spelling authority |

Inside the imported files, left out on purpose: EVS's Russian government
(`vrek`, "о ком-чём") and its example phrases, VSL's etymology, HAR's Estonian
definitions and its English, German and Finnish, EKSS's examples. Each would
be a second answer in a slot the card already fills, or a slot a learner at A2
has no use for.

`evs` is 87 MB raw, over GitHub's 50 MB warning; gzipped it is 15 MB, and every
importer reads `.gz` directly. The raw XML and the last four rows stay
git-ignored.

## The shape is not the schema

The first real run of `import-psv` failed on byte one — "unbound prefix: line 1,
column 0" — after a clean suite against a fixture built from `schema_psv.xsd`.
The files have no root element and undeclared namespace prefixes, one article
per line. `eesti/ekixml.py` reads that shape, and has the entity codes and
marks that had to be cleaned. Run `--check` before importing a new download:

```bash
python -m eesti.cli import-levels deploy/eki/A1A2B1.txt --check
python -m eesti.cli import-psv    deploy/eki/psv_EKI_CCBY40.xml.gz --check
python -m eesti.cli import-evs    deploy/eki/evs_EKI_CCBY40.xml.gz --check
python -m eesti.cli import-vsl    deploy/eki/vsl_EKI_CCBY40.xml.gz --check
python -m eesti.cli import-har    deploy/eki/har_EKI_CCBY40.xml.gz --check
python -m eesti.cli import-ekss   deploy/eki/ekss_EKI_CCBY40.xml.gz --check
```

Drop `--check` to import. All of it is reference data in the words database,
which is baked into the image — not in `vocab.db`, which a state-snapshot
restore replaces whole.

To refresh a file: download it, `gzip -9 -n`, replace it here, run `--check`,
and commit.
