"""Command line entry points.

    python -m eesti.cli fetch-data    # download the word list (one time, ~2.8 MB)
    python -m eesti.cli build         # import + index object cases
    python -m eesti.cli drill -n 10   # practise in the terminal
    python -m eesti.cli check "..."   # grammar check a sentence
    python -m eesti.cli serve         # local web app
"""

# This docstring is what `--help` prints, so it stays short and about the tool.
#
# The package was one 1 620-line module in which every command's flags sat in a
# single argparse block at the bottom, a thousand lines from the function that
# read them. Commands are grouped by what they are for now, and each group
# registers its own subparsers, so a flag and its handler are on one screen.
#
# `main` and every `cmd_*` are re-exported here, because `eesti.cli` is the
# name the tests, the Dockerfile and the deploy scripts use.

from __future__ import annotations

import argparse

from . import assess, build, harvest, ops, report, study

#: Registration order, which is the order `--help` lists the commands in.
#: Build what the app runs on, fill the library, practise, be measured, look at
#: where you stand, operate the deployment.
GROUPS = (build, harvest, study, assess, report, ops)

# `eesti.cli.cmd_status` and friends keep working: the tests, and anything that
# imported a handler by name, address this package rather than a module inside
# it. Derived from the groups rather than written out, because a list of 36
# names maintained by hand is the thing this project has a rule against -- and
# the list would be wrong the first time a command moved between groups.
for _group in GROUPS:
    globals().update({name: value for name, value in vars(_group).items()
                      if name.startswith("cmd_")})


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="eesti", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    for group in GROUPS:
        group.register(sub)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
