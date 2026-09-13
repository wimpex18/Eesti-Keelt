# EKI's dictionary downloads, committed

Five files from <https://arhiiv.eki.ee/litsents/>, all CC BY 4.0, committed here
since 2026-09-13 and imported by the `Dockerfile` into `data/eesti.db`. The
learner downloaded them — direct links worked that day, without the ID-card
step recorded on 2026-09-12 — and nothing in this repo fetches from EKI.

| File | What it is | What it turns on |
|---|---|---|
| `A1A2B1.txt` | *Eesti keele tasemete sõnavara* — 4 456 lemmas, A1 740 · A2 1 266 · B1 2 450 | `words.level` is EKI's answer, `words.level_source` says so |
| `psv_EKI_CCBY40.xml.gz` | *Eesti keele põhisõnavara sõnastik* — 4 849 learner-level definitions | the word card's definition and examples |
| `evs_EKI_CCBY40.xml.gz` | *Eesti-vene sõnaraamat* — 60 610 lemmas with Russian | the word card's and the drills' Russian, offline |
| `vsl_EKI_CCBY40.xml.gz` | *Võõrsõnade leksikon* — 30 095 definitions | last-fallback definition |
| `har_EKI_CCBY40.xml.gz` | *Haridussõnastik* — 5 873 terms with Russian | last-fallback Russian |

Counts measured on the real files, 2026-09-13. EKI's terms: process and present
the material any way needed, an app included, provided the attribution stays and
the changes are described. Both live in `eesti/licences.py`, and `/api/sources`
serves them; the word card credits EKI on whatever EKI wrote.

## Which answer a word card shows

Every source has its own table, and none writes another's:

- **Estonian definition** — PSV (`psv_gloss`) → live Sõnaveeb → VSL, then EKSS if imported
- **Russian** — EVS (`evs_gloss`) → live Sõnaveeb → HAR (`har_gloss`)

Stated in code once, in `eesti/api/grammar.py` (`_meaning`, `_russian`).

## Why gzipped, and what is not here

`evs` is 87 MB raw, over GitHub's 50 MB warning; gzipped it is 15 MB, and every
importer reads `.gz` directly. The raw XML, the `.xsd` schemas, `ekss` (the full
explanatory dictionary, 68 MB — Sõnaveeb shows it live, so it is optional) and
the extras (`scrabble.txt`, `marksonad.txt`, `ekss.html.gz`) stay git-ignored.

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
