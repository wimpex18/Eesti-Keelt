"""`python -m eesti.cli`. Guarded so that importing the package's modules (e.g. a
check that imports every module) does not run the parser.
"""

from __future__ import annotations

from . import main

if __name__ == "__main__":
    raise SystemExit(main())
