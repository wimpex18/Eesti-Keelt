"""The reference imports, and whether a deployment can tell they ran.

EKK's rection table and the EKI dictionaries are imported at image build and
may fail without failing it, so `/api/health` reports row counts (not flags) and
the smoke workflow reads them.
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
    """Each import command is run by the Dockerfile, which ends each step in `||`."""

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

    def test_every_file_the_image_imports_is_in_git(self):
        """Every file the Dockerfile imports is tracked by git (Cloud Build checks out
        git), derived from the Dockerfile.
        """
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
        """File names agree between the Dockerfile, the CLI's messages and
        `docs/sources.md`.
        """
        dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
        cli = (ROOT / "eesti" / "cli" / "build.py").read_text(encoding="utf-8")
        readme = (ROOT / "docs" / "sources.md").read_text(encoding="utf-8")
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
        assert "docs/sources.md" in eki
        assert "rections" not in eki, "the EKI hint must not name `cli rections`"
