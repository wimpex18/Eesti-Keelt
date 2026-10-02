"""Reproducible public inputs and the image's evidence about what it contains."""
from __future__ import annotations

import hashlib
import json
import platform
from functools import lru_cache
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

# The latest file-changing upstream commit, verified against the local bytes.
WORDLIST_REVISION = "5f9504f0d86d0280bbb20f1e2c77e9688eef7c90"
WORDLIST_BASE = (
    "https://raw.githubusercontent.com/KristjanPikhof/"
    f"Estonian-Wordlist-Enriched-Ekilex/{WORDLIST_REVISION}/data"
)
WORDLIST_SHA256 = {
    "est_words_160k.tsv": "552ea36af251c699f01eeb42821dfde26b6ec936fbed93645f2aaf5afa6dfac5",
}
WORDLIST_FILES = tuple(WORDLIST_SHA256)


def build_inputs(raw: Path | None = None, eki: Path | None = None) -> dict:
    """Fingerprint build inputs; imported row counts remain a separate report.

    These hashes identify bytes, not the latest authenticated EKI download.
    """
    from . import config
    raw = Path(raw or config.RAW)
    eki = Path(eki or config.ROOT / "deploy" / "eki")
    result = {}
    for name in WORDLIST_FILES:
        path = raw / name
        if path.is_file():
            body = path.read_bytes()
            digest = hashlib.sha256(body).hexdigest()
            result[name] = {"sha256": digest, "bytes": len(body),
                            "url": f"{WORDLIST_BASE}/{name}",
                            "revision": WORDLIST_REVISION,
                            "verified": digest == WORDLIST_SHA256[name]}
    for path in sorted(eki.glob("*")):
        if path.is_file() and (path.name.endswith(".xml.gz") or path.name == "A1A2B1.txt"):
            body = path.read_bytes()
            result[path.name] = {"sha256": hashlib.sha256(body).hexdigest(),
                                 "bytes": len(body), "url": "https://arhiiv.eki.ee/litsents/"}
    return result


@lru_cache(maxsize=1)
def deployment_inputs() -> dict:
    try:
        return json.loads(Path("/app/REFERENCE_INPUTS.json").read_text())
    except (OSError, ValueError):
        return {}  # A checkout cannot attest what a previous database build used.


@lru_cache(maxsize=1)
def dependencies() -> dict:
    result = {"python": platform.python_version()}
    for package in ("estnltk", "fastapi", "uvicorn", "fsrs", "pypdf", "pypdfium2", "pdfplumber", "Pillow"):
        try:
            result[package] = version(package)
        except PackageNotFoundError:
            result[package] = None
    return result


if __name__ == "__main__":
    print(json.dumps(build_inputs(), ensure_ascii=False, sort_keys=True))
