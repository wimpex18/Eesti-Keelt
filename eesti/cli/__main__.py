"""`python -m eesti.cli` — the way every document here says to run this.

Guarded, though a `__main__.py` is only ever *run*: anything that walks the
package and imports what it finds — a doc generator, a check that imports every
module to see that it imports — would otherwise run the command line parser and
exit the process it was walking from. It cost one confusing traceback to find
that out, and the guard is one line.
"""

from __future__ import annotations

from . import main

if __name__ == "__main__":
    raise SystemExit(main())
