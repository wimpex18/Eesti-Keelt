# EKI's dictionary downloads, committed

Five files from <https://arhiiv.eki.ee/litsents/>, all CC BY 4.0, committed here
since 2026-09-13 and imported by the `Dockerfile` into `data/eesti.db`. The
learner downloaded them — direct links worked that day, without the ID-card
step recorded on 2026-09-12 — and nothing in this repo fetches from EKI.

| File | What it is | What it turns on |
|---|---|---|
| `A1A2B1.txt` | *Eesti keele tasemete sõnavara* — 4 456 lemmas, A1 740 · A2 1 266 · B1 2 450 | `words.level` is EKI's answer, `words.level_source` says so |
| `psv_EKI_CCBY40.xml.gz` | *Eesti keele põhisõnavara sõnastik* — 4 849 learner-level definitions | the word card's definition and examples |
| `evs_EKI_CCBY40.xml.gz` | *Eesti-vene sõnaraamat* — 60 509 lemmas with Russian | the word card's and the drills' Russian, offline |
| `vsl_EKI_CCBY40.xml.gz` | *Võõrsõnade leksikon* — 30 095 definitions | last-fallback definition |
| `har_EKI_CCBY40.xml.gz` | *Haridussõnastik* — 5 871 terms with Russian | last-fallback Russian |

Counts measured on the real files, 2026-09-13. EKI's terms: process and present
the material any way needed, an app included, provided the attribution stays and
the changes are described. Both live in `eesti/licences.py`, and `/api/sources`
serves them; the word card credits EKI on whatever EKI wrote.

## Where the learner meets it, and in which order

Every source keeps its own table, and none writes another's.

- **Russian** — seed glossary → EVS → Sõnaveeb → HAR, stated once in
  `eesti/meaning.py` and used by every flow that shows a meaning: the word card
  (Lugemine and Sõnavara), the Sõnavara list, the gloss beside a drill, the
  gloss after a graded answer, and the review flashcard made with *Kordamisse*.
  The seed (294 hand-written glosses for the drill words) outranks EVS because
  EVS puts a different first translation on 45 of them — `kohus` "долг", not "суд".
- **Estonian definition and examples** — PSV → Sõnaveeb → VSL (→ EKSS if
  imported), on the word card: `eesti/api/grammar.py`, `_meaning`.
- **CEFR level** — EKI's list over the estimate, everywhere a level is shown or
  filtered (`words.level_source`), as before.

Nothing needs the learner to open a file; the card credits EKI on whatever EKI
wrote, and `Allikad` lists every source with its changes.

## Every file in the download, and what became of it

| File | Used? | Why |
|---|---|---|
| `A1A2B1.txt`, `psv`, `evs`, `vsl`, `har` `_EKI_CCBY40.xml` | imported, committed gzipped | above |
| `ekss_EKI_CCBY40.xml` | optional `cli import-ekss`, not committed | the full native dictionary, 68 MB; Sõnaveeb shows the same definitions live |
| `schema_*.xsd`, `*_tyybid.xsd` | read, not imported | EKI's code lists: the style labels (`van`, `kõnek`, `hlv`…, `halb` in HAR) and the `l="ka"` "also" qualifier that decide which translation comes first |
| `ekss.html.gz` | read, not used | an HTML rendering of the same EKSS articles |
| `marksonad.txt` | read, not used | EKSS's 138 392 headwords with nothing attached; the word list already has 160 316 |
| `scrabble.txt` | read, not used | 136 771 lowercase word forms for a word game; Vabamorf is this app's spelling authority |

`evs` is 87 MB raw, over GitHub's 50 MB warning; gzipped it is 15 MB, and every
importer reads `.gz` directly. Everything in the last four rows stays
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
python -m eesti.cli import-ekss   path/to/ekss_EKI_CCBY40.xml      --check   # optional
```

Drop `--check` to import. All of it is reference data in the words database,
which is baked into the image — not in `vocab.db`, which a state-snapshot
restore replaces whole.

To refresh a file: download it, `gzip -9 -n`, replace it here, run `--check`,
and commit.
