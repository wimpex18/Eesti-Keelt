"""Local cleanup removes only named skills and never follows deletion symlinks."""
import importlib.util
from pathlib import Path


def test_cleanup_targets_codex_and_claude_copies_but_preserves_other_skills(tmp_path):
    spec = importlib.util.spec_from_file_location("skill_cleanup", Path(__file__).parents[1] / "deploy/remove-local-skills.py")
    cleanup = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cleanup)
    home, project = tmp_path / "home", tmp_path / "project"
    folders = [(home / ".codex/skills/product-qa", "product-qa"),
               (home / ".claude/skills/qa-product", "QA product"),
               (home / ".agents/skills/wanderalt", "WanderAlt"),
               (home / ".codex/skills/impeccable", "impeccable"),
               (home / ".claude/skills/python", "python"),
               (project / ".claude/skills/impeccable", "impeccable")]
    for folder, name in folders:
        folder.mkdir(parents=True)
        (folder / "SKILL.md").write_text(f"---\nname: {name}\n---\n")
    outside = tmp_path / "outside/wanderalt"
    outside.mkdir(parents=True)
    (outside / "SKILL.md").write_text("---\nname: WanderAlt\n---\n")
    linked = project / ".claude/skills/wanderalt"
    linked.symlink_to(outside, target_is_directory=True)
    matches = cleanup.targets(home, project)
    assert set(matches) == {folders[i][0] for i in (0, 1, 2, 5)} | {linked}
    cleanup.remove(matches)
    assert all(not path.exists() for path in matches)
    assert outside.is_dir()
    assert folders[3][0].is_dir() and folders[4][0].is_dir()
