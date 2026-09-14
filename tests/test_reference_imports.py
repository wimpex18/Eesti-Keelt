"""The reference imports, and whether a deployment can tell they ran.

All three — EKK's rection table, EKI's level vocabulary, EKI's learner
dictionary — happen at image build time and are all allowed to fail without
failing the build. `cli rections` needs EKI to answer a datacenter IP, and they
have already returned 403 to a GitHub runner on that exact URL; the two EKI
downloads need files a person has to fetch from behind ID-card authentication. Failing the
image on any of them would trade one feature for the whole deploy.

That trade is only defensible if the deployment can be *asked* which ones
landed — otherwise "never imported" and "imported and empty" look identical
from outside, which is this project's oldest recurring bug in a new costume
(`.claude/rules/python.md`). Hence counts, not flags,
and a check in the smoke workflow that reads them.
"""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

FIELDS = ("rections", "eki_levels", "eki_definitions", "eki_russian",
          "eki_terms", "eki_loanwords", "eki_explanatory")


class TestHealthReportsThem:
    def test_all_three_are_counted(self, client):
        got = client.get("/api/health").json()["reference"]
        assert set(got) == set(FIELDS)
        assert all(isinstance(got[f], int) for f in FIELDS)

    def test_a_deployment_that_imported_nothing_reads_zero_not_missing(
        self, client, monkeypatch, tmp_path
    ):
        """Zero and absent say different things, and only one of them is
        actionable. A words database nobody has imported into must answer 0
        three times rather than raise or drop the key."""
        from eesti import config, wordlist

        empty = tmp_path / "bare.db"
        wordlist.connect(empty).close()
        monkeypatch.setattr(config, "DB_PATH", empty)

        got = client.get("/api/health").json()
        assert got["words"] == 0, "and the fixture really is empty"
        assert got["reference"] == {f: 0 for f in FIELDS}


class TestTheBuildActuallyRunsThem:
    """A command nothing calls is a command that never ran. All three sat in
    the CLI with no caller on the deployment, which is why every one of these
    counts was zero in production while the code to fill them was shipped."""

    @pytest.fixture
    def dockerfile(self):
        return (ROOT / "Dockerfile").read_text(encoding="utf-8")

    @pytest.mark.parametrize("command", ["rections", "import-levels", "import-psv", "import-evs", "import-vsl", "import-har", "import-ekss"])
    def test_the_image_build_runs_it(self, dockerfile, command):
        assert f"eesti.cli {command}" in dockerfile

    @pytest.mark.parametrize("command", ["rections", "import-levels", "import-psv", "import-evs", "import-vsl", "import-har", "import-ekss"])
    def test_and_is_allowed_to_fail(self, dockerfile, command):
        """Each depends on a third party or on a file a person downloaded.
        Chained with `&&`, somebody else's bad afternoon takes down the deploy."""
        line = next(l for l in dockerfile.splitlines() if f"eesti.cli {command}" in l)
        assert line.rstrip().endswith("|| \\"), line

    def test_the_eki_drop_directory_survives_an_empty_build_context(self):
        """Docker has no conditional COPY, so the directory the two EKI files
        go in has to exist in the repo with something committed in it. Empty,
        the COPY fails and the image will not build for someone who has not
        filled in EKI's form."""
        readme = ROOT / "deploy" / "eki" / "README.md"
        assert readme.exists(), "the COPY in the Dockerfile has nothing to copy"
        ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
        assert "deploy/eki/*" in ignore
        assert "!deploy/eki/README.md" in ignore, "and the README must survive it"

    def test_every_file_the_image_imports_is_in_git(self):
        """Cloud Build builds from a git checkout, so a file the Dockerfile
        imports and git ignores is a file production never has. That was the
        state until 2026-09-13 — smoke read `eki_levels` 0 and
        `eki_definitions` 0 — while the README promised "baked into the next
        image". Derived from the Dockerfile, so a new import cannot repeat it."""
        import re
        import subprocess

        dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
        imported = sorted(set(re.findall(r"eesti\.cli import-\w+ (deploy/eki/\S+)", dockerfile)))
        assert imported, "the Dockerfile imports nothing from deploy/eki"
        ignored = subprocess.run(
            ["git", "check-ignore", "--no-index", *imported],
            cwd=ROOT, capture_output=True, text=True).stdout.split()
        assert not ignored, f"git ignores what the image imports: {ignored}"

    def test_the_file_names_agree_with_what_the_cli_tells_you_to_download(self):
        """The Dockerfile looks for a fixed name; the CLI prints one. They
        drifted once already — `tasemesonavara.txt` against `A1A2B1.txt` — and
        a build that silently skips the import is exactly what that costs."""
        dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
        cli = (ROOT / "eesti" / "cli" / "build.py").read_text(encoding="utf-8")
        readme = (ROOT / "deploy" / "eki" / "README.md").read_text(encoding="utf-8")
        for name in ("A1A2B1.txt", "psv_EKI_CCBY40.xml", "evs_EKI_CCBY40.xml",
                     "vsl_EKI_CCBY40.xml", "har_EKI_CCBY40.xml"):
            assert f"deploy/eki/{name}" in dockerfile, name
            assert name in cli, name
            assert name in readme, name


class TestTheSmokeCheckReadsThem:
    def test_the_deployment_check_asks_for_each_one(self):
        body = (ROOT / ".github" / "workflows" / "smoke.yml").read_text(
            encoding="utf-8")
        assert ".reference[$k]" in body
        for field in FIELDS:
            assert field in body, field

    def test_each_missing_field_is_told_its_own_fix(self):
        """One hint served all three and told a missing `eki_levels` to "run
        'cli rections'", which fills a different table. A warning that names
        the wrong command sends the operator to do something that cannot help."""
        body = (ROOT / ".github" / "workflows" / "smoke.yml").read_text(
            encoding="utf-8")
        start = body.index('case "$f" in')
        block = body[start:body.index("esac", start)]
        rections, _, eki = block.partition("*)")
        assert "rections)" in rections and "eesti.cli rections" in rections
        assert "deploy/eki/README.md" in eki
        assert "rections" not in eki, "the EKI hint must not name `cli rections`"
