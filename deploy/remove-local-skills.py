"""Remove the user-requested QA/product and WanderAlt skills on a local machine.

Preview: python3 deploy/remove-local-skills.py
Remove:  python3 deploy/remove-local-skills.py --apply
Run from the local Eesti-Keelt checkout. Symlinks are unlinked, never followed
for deletion. Candidate names come from directory names and SKILL.md metadata.
"""
from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path


def named_target(folder: Path) -> bool:
    skill = folder / "SKILL.md"
    if not skill.is_file():
        return False
    text = skill.read_text(encoding="utf-8")
    metadata = "\n".join(line for line in text.splitlines()[:40]
                         if re.match(r"^(name:|description:|# )", line))
    words = re.sub(r"[^a-z0-9]+", " ", folder.name.lower() + " " + metadata.lower())
    tokens = set(words.split())
    qa_product = "product" in tokens and ("qa" in tokens or "quality assurance" in words)
    return qa_product or "wanderalt" in tokens


def targets(home: Path, project: Path) -> list[Path]:
    found = []
    roots = [base / name / "skills" for base in (home, project) for name in (".codex", ".agents", ".claude")]
    for root in roots:
        if root.is_dir():
            found.extend(path for path in sorted(root.iterdir())
                         if path.is_dir() and named_target(path))
    return list(dict.fromkeys(found))


def remove(paths: list[Path]) -> None:
    for path in paths:
        if path.is_symlink():
            path.unlink()
        else:
            shutil.rmtree(path)
        print("Removed " + str(path))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="remove the exact matching skill folders")
    parser.add_argument("--home", type=Path, default=Path.home(), help="home directory to inspect")
    parser.add_argument("--project", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    paths = targets(args.home, args.project)
    if not paths:
        print("No matching QA/product or WanderAlt skill folders found.")
    elif args.apply:
        remove(paths)
    else:
        print("Matching skill folders:")
        for path in paths:
            print(path)
        print("Run with --apply to remove these folders.")


if __name__ == "__main__":
    main()
