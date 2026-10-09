"""`cli worktree-data`: a parallel session's worktree gets the reference data.

What the owner would notice if this broke: an agent's server or tests in another
worktree writing into the owner's own learning history, or the owner's voice
recordings copied into a checkout another session works in.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from eesti import config
from eesti.cli.ops import cmd_worktree_data


def _touch(path: Path, text: str = "x") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def test_reference_data_is_copied_and_the_learner_s_own_is_not(tmp_path, monkeypatch):
    source, target = tmp_path / "main", tmp_path / "wt"
    reference = ["eesti.db", "content.db", "audio.db", "cache/evkk.json", "exam/b1.pdf"]
    private = [*config._LEARNER_FILES.values(), "learners/a/progress.db",
               "guest/g/events.db", "eval/asr/clip.wav"]
    for name in reference + private:
        _touch(source / "data" / name)
    _touch(target / "data" / "eesti.db", "kept")   # never overwritten
    monkeypatch.chdir(target)

    assert cmd_worktree_data(argparse.Namespace(source=str(source))) == 0

    for name in reference:
        assert (target / "data" / name).exists(), name
    assert (target / "data" / "eesti.db").read_text() == "kept"
    for name in private:
        assert not (target / "data" / name).exists(), name


def test_it_refuses_to_copy_a_checkout_onto_itself(tmp_path, monkeypatch):
    _touch(tmp_path / "data" / "eesti.db")
    monkeypatch.chdir(tmp_path)
    assert cmd_worktree_data(argparse.Namespace(source=str(tmp_path))) == 1
