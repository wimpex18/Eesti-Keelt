# The phantom word list — found, and how

**Answer: it was never the test suite.** `python -m eesti.cli status`, `themes`,
`vocab`, `readiness`, `drill`, `conjugate`, `patterns` and `placement`, typed
before `cli build`, each read the lexicon through `wordlist.connect()` — which
creates the file and applies the schema. Reading it made one. They go through
`cli/_helpers.words_db` now, which asks `available()` first.

This directory is what found it, and is kept for the next one. The hook is the
same one `conftest.py` installs, injected through `PYTHONPATH` so it also loads
in every subprocess the suite spawns — the half an in-process monkeypatch of
`sqlite3.connect` cannot see, and the reason the first spy came back empty:
`PYTHONPATH` is inherited, a patched attribute is not.

Python imports `sitecustomize` automatically at startup if it is importable,
which is what makes this work without any test knowing about it.

## Running the hunt

The phantom only appears when the file is absent, so park the real word list
first — and **put it back afterwards**, it is 160 316 rows and ~30 minutes of
`cli build`:

```bash
mv data/eesti.db /tmp/eesti.db.real          # park it

rm -f /tmp/phantom.log
PYTHONPATH=tests/phantom \
PHANTOM_LOG=/tmp/phantom.log \
PHANTOM_TARGET="$PWD/data/eesti.db" \
  python -m pytest tests/ -q

ls -la data/eesti.db                          # did one appear?
cat /tmp/phantom.log                          # who opened it, and from which pid

mv /tmp/eesti.db.real data/eesti.db          # put it back
```

`argv` on each log entry is the giveaway: `['-c', ...]` is a `python -c`
subprocess, `['-m', 'uvicorn', ...]` is the e2e server, and a pytest argv is an
in-process call the conftest guard would also have caught.

## What was ruled out, and how

| | |
|---|---|
| every test in the pytest process | the autouse fixture in `conftest.py` redirects `config.DB_PATH` for all of them |
| `test_cli_smoke` | calls `cli.main()` **in-process** — it runs all eight culprits and could never show the bug |
| `test_route_inventory`, `test_secret_placement`, `test_speaking` | shell out to `grep`/`sed`/`sh`, never Python |
| `test_e2e_journeys` | ruled out by construction — see below |
| the suite as a whole | five full runs under this hook logged **not one** read-write open of that path |

## Why the uvicorn subprocess was not a suspect

It looks like the best candidate — the one subprocess that runs the whole
application — and it cannot be the writer. `live_server` opens with:

```python
if not available(words) or not content.exists():
    pytest.skip("no built dataset — run `python -m eesti.cli build`")
```

The phantom only appears when the word list is **absent**, and that gate skips
the entire journey suite when it is. The server never starts in the one
condition where it could create the file; in the other the file is already
there. Either way, not it.

That also means the hunt cannot cover the journeys: parking the word list is
what makes the phantom possible and is exactly what makes them skip. A property
of the bug, not a gap in the method.

## The cheaper check, first

A full suite run is minutes. Reproducing it directly is seconds, and is how it
was actually found — run the commands, not the tests:

```bash
mv data/eesti.db /tmp/eesti.db.real
for c in status themes vocab "readiness --level A2" "drill -n 2"; do
  rm -f data/eesti.db
  python -m eesti.cli $c >/dev/null 2>&1
  [ -f data/eesti.db ] && echo "CREATED BY: cli $c"
done
rm -f data/eesti.db; mv /tmp/eesti.db.real data/eesti.db
```

Use the command's **real** argument form. `cli readiness A2` looked clean only
because argparse rejected it before the code ran; `cli readiness --level A2`
created the file. `tests/test_phantom_wordlist.py` now derives the list from
`test_cli_smoke.READ_ONLY` so nobody has to remember that.
