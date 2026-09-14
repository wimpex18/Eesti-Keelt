# EKI dictionary files

CC BY 4.0 downloads from <https://arhiiv.eki.ee/litsents/>, committed here and
imported by the `Dockerfile` into `data/eesti.db`. Nothing in the repo fetches
from EKI. Attribution lives in `eesti/licences.py` and is served at
`/api/sources`; the word card credits EKI on whatever EKI wrote.

| File | Contents | Import | Used for |
|---|---|---|---|
| `A1A2B1.txt` | *Eesti keele tasemete sõnavara*, 4 456 lemmas | `cli import-levels` | official CEFR level (`words.level_source = 'eki'`) |
| `psv_EKI_CCBY40.xml.gz` | *põhisõnavara sõnastik*, 4 849 learner definitions | `cli import-psv` | word card definition, examples, rection |
| `evs_EKI_CCBY40.xml.gz` | *Eesti-vene sõnaraamat*, 60 672 lemmas with Russian | `cli import-evs` | offline Russian, inflection type |
| `vsl_EKI_CCBY40.xml.gz` | *Võõrsõnade leksikon*, 30 095 definitions | `cli import-vsl` | fallback definition |
| `har_EKI_CCBY40.xml.gz` | *Haridussõnastik*, 5 905 terms with Russian | `cli import-har` | fallback Russian |
| `ekss_EKI_CCBY40.xml.gz` | *seletav sõnaraamat*, 117 937 definitions | `cli import-ekss` | fallback definition |

## Lookup order

- **Russian:** seed glossary → live dictionary (Ekilex / Sõnaveeb) → EVS → HAR
  (`eesti/meaning.py`). The seed names the sense the drills use.
- **Definition:** PSV → live → VSL → EKSS (`eesti/api/grammar.py`); when PSV
  answers, the native-level wording is folded under *täpsem seletus*.
- **Rektsioon, muuttüüp:** live, else PSV rection and EVS type.

Not imported: EVS government and examples, VSL etymology, HAR's other
languages, EKSS examples, and `marksonad.txt`, `ekss.html.gz`, `scrabble.txt`
(duplicates or no meaning attached).

## The file shape

The XML has no root element and undeclared namespace prefixes, one article per
line; `eesti/ekixml.py` reads that shape. Headwords mark compound boundaries
with `+`, `|` or `\`. Check a new download before importing:

```bash
python -m eesti.cli import-psv deploy/eki/psv_EKI_CCBY40.xml.gz --check
```

To refresh a file: download it, `gzip -9 -n`, replace it here, run `--check`
with the matching `import-*` command, commit. Raw XML, schemas and extras stay
git-ignored.
