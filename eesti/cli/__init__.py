"""Command line entry points.

    python -m eesti.cli fetch-data    # download the word list (one time, ~2.8 MB)
    python -m eesti.cli build         # import + index object cases
    python -m eesti.cli drill -n 10   # practise in the terminal
    python -m eesti.cli check "..."   # grammar check a sentence
    python -m eesti.cli serve         # local web app
"""

# This docstring is what `--help` prints. Commands are grouped by purpose and each
# group registers its own subparsers beside its handlers. `main` and every `cmd_*`
# are re-exported, because `eesti.cli` is the name tests, the Dockerfile and deploy
# scripts use.

from __future__ import annotations

import argparse

from . import assess, build, harvest, ops, report, study
from ._helpers import (  # noqa: F401  -- part of `eesti.cli`'s surface
    content_db,
    content_path,
    learner_db,
    words_db,
)

#: Registration order, which is the order `--help` lists the commands in.
#: Build what the app runs on, fill the library, practise, be measured, look at
#: where you stand, operate the deployment.
GROUPS = (build, harvest, study, assess, report, ops)

# Re-export every handler, derived from the groups.
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
