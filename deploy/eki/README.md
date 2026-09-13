# Two files EKI hands over in person

Drop them here and a `docker build` **from this working copy** bakes them in.
The deployed image is not built from this working copy — see *The deployment
does not have them* below. Nothing in this repo
downloads them, and that is deliberate: EKI serve both behind **ID-card
authentication** (checked 2026-09-12), which is a gate to walk through rather
than step around. It also means you need an Estonian ID card or Mobiil-ID to
get them at all — worth knowing before planning a build around their being
here.

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
python -m eesti.cli import-psv    deploy/eki/psv_EKI_CCBY40.xml --check   # first, always
python -m eesti.cli import-psv    deploy/eki/psv_EKI_CCBY40.xml
```

`import-psv --check` matters more than the other one: `eesti/psv.py` has only
ever read a fixture built from EKI's schema, and EKI say their XML does not
validate against it. If it reports headwords and no definitions, the parser
does not fit the real file — fix it against the file, not against the schema.

Locally that is all. The `Dockerfile` runs the same two commands during the
build, against whatever is sitting in this directory — so a `docker build` with
the files present ships a word list EKI levelled and a dictionary a learner can
read, and a build without them ships exactly what it shipped before. Both write into `data/eesti.db`, which is baked into the image:
reference data, the same for everybody, and **not** carried by the state
snapshot — a restore replaces `vocab.db`, `progress.db` and `review.db` whole,
so anything kept there would vanish on the first cold start.

The files themselves are git-ignored. They are redistributable under CC BY 4.0,
but this repo's rule is that data files are built or downloaded, never
committed, and 51 015 rows of someone else's list is not a diff anybody reads.

## The deployment does not have them

Cloud Build rebuilds the production image on every merge to `main`, from git.
These files are git-ignored — the line below says why — so that build never
sees them, both imports print "not found", and the `||` lets the image ship
without them. Measured on 2026-09-13: smoke run 34765657703 read `eki_levels` 0
and `eki_definitions` 0 from an image built three minutes after the merge.

`gcloud builds submit` from a working copy that holds them would not help
either: without a `.gcloudignore`, gcloud honours `.gitignore` and leaves them
out of the upload.

So getting them into production is a decision nobody has made yet, and it
waits until someone actually holds the files. The two shapes it can take are
committing them (CC BY 4.0 permits it; this repo's rule against committed data
files would need an exception) or having the build fetch them from a private
bucket. Until then the importers have met the level list only through facts
read off it (`docs/source-audit.md`) and the dictionary XML **not at all** —
`psv.py` is tested against a fixture built from the schema.

The file names above are what the `Dockerfile` looks for. If EKI hand you a
different name, rename it — or run the commands yourself and rebuild.
