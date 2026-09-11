# Two files EKI hands over in person

Drop them here and they are baked into the next image. Nothing in this repo
downloads them, and that is deliberate: EKI serves both behind a form asking
who you are and what the material will be used in, and answering that is worth
doing rather than stepping around.

| File | What it is | What it turns on |
|---|---|---|
| `A1A2B1.txt` | *Eesti keele tasemete sõnavara* (2018) — the official A1 / A2 / B1 lists | `words.level` becomes EKI's answer instead of an estimate; `words.level_source` says so |
| `psv_EKI_CCBY40.xml` | *Eesti keele põhisõnavara sõnastik* (2014) — ~6 000 words defined in language a learner can read | the word card shows a definition the learner can read, with real usage examples |

Both from <https://arhiiv.eki.ee/litsents/>, both CC BY 4.0. EKI's terms: process
and present the material any way you need, an app included, provided the
attribution stays and the changes are described. Both are described in
`eesti/sources.py`, which is where the attribution lives.

## Getting them in

```bash
python -m eesti.cli import-levels deploy/eki/A1A2B1.txt --check   # read it, write nothing
python -m eesti.cli import-levels deploy/eki/A1A2B1.txt
python -m eesti.cli import-psv    deploy/eki/psv_EKI_CCBY40.xml
```

Locally that is all. On the deployment the `Dockerfile` runs the same two
commands during the build, against whatever is sitting in this directory — so a
`docker build` with the files present ships a word list EKI levelled and a
dictionary a learner can read, and a build without them ships exactly what it
shipped before. Both write into `data/eesti.db`, which is baked into the image:
reference data, the same for everybody, and **not** carried by the state
snapshot — a restore replaces `vocab.db`, `progress.db` and `review.db` whole,
so anything kept there would vanish on the first cold start.

The files themselves are git-ignored. They are redistributable under CC BY 4.0,
but this repo's rule is that data files are built or downloaded, never
committed, and 51 015 rows of someone else's list is not a diff anybody reads.

The file names above are what the `Dockerfile` looks for. If EKI hand you a
different name, rename it — or run the commands yourself and rebuild.
