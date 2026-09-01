"""Catch whatever creates an empty `data/eesti.db`, including in subprocesses.

`tests/conftest.py` carries a guard that reports the phantom at the end of the
run that made it, with a stack when the call was in-process. This is the other
half: the same hook, injected through `PYTHONPATH`, so it also loads in every
subprocess the suite spawns.

That distinction is the whole reason the phantom stayed unpinned for so long.
No test in the pytest process can create it -- the autouse fixture in
`conftest.py` redirects `config.DB_PATH` for every one of them -- and a
monkeypatch of `sqlite3.connect` in this interpreter is invisible in another.
`PYTHONPATH` is inherited; a monkeypatched attribute is not.

Python imports `sitecustomize` automatically at startup if it is importable,
which is what makes this work without any test knowing about it.

    tests/phantom/README.md has the command.

Three rules, each learned by getting it wrong first -- see the same three in
`conftest._watch_for_the_phantom`:

* match the **absolute path**, not the basename: the session fixture builds its
  own word list and also calls it `eesti.db`;
* ignore **read-only** opens: `wordlist.available` opens `mode=ro` to ask
  whether the file exists, and cannot create anything;
* record the **first** creating call only, since everything after it opens a
  file that now exists.
"""

import os
import sys
import traceback

_LOG = os.environ.get("PHANTOM_LOG")
_TARGET = os.environ.get("PHANTOM_TARGET")


def _install() -> None:
    target = os.path.realpath(_TARGET)

    def hook(event, args):
        if event != "sqlite3.connect":
            return
        try:
            raw = str(args[0])
        except Exception:
            return
        if "mode=ro" in raw:
            return
        opened = raw.replace("file:", "").split("?")[0]
        try:
            if os.path.realpath(opened) != target:
                return
        except OSError:
            return
        with open(_LOG, "a", encoding="utf-8") as fh:
            fh.write(f"\n=== pid {os.getpid()}  argv={sys.argv[:4]}\n")
            fh.write("".join(traceback.format_stack()[:-1]))

    sys.addaudithook(hook)


if _LOG and _TARGET:
    _install()
