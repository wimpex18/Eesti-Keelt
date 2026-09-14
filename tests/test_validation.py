"""Foundation checks against third-party data; skipped when the benchmark files
are absent.
"""

import json

import pytest

from eesti.evals.morphology import DATASET, run
from eesti.sources import REGISTRY, Item, add_items, connect, query, register

pytestmark = pytest.mark.skipif(
    not DATASET.exists(), reason="run `python -m eesti.cli fetch-bench` first"
)


def test_vabamorf_agrees_with_native_gold_forms():
    """Vabamorf matches TalTech's native-curated inflections (threshold 95 %, below
    the measured ~98 %).
    """
    result = run()
    assert result["total"] > 1000, "dataset looks truncated"
    assert result["agreement"] >= 0.95, (
        f"agreement fell to {result['agreement']:.1%} — "
        "Vabamorf output no longer matches gold forms"
    )


@pytest.mark.parametrize("case", ["sg g", "sg p"])
def test_object_cases_specifically_agree(case):
    """The two cases the whole app rests on get their own gate."""
    match, total = run()["per_case"][case]
    assert match / total >= 0.95, f"{case} agreement dropped to {match}/{total}"


@pytest.mark.parametrize(("name", "least"), [("grammar_et", 500), ("grammar2_et", 300)])
def test_grammar_benchmark_is_wellformed(name, least):
    """Every GEC pair file the drill reads actually contains differing pairs."""
    path = DATASET.parent / f"{name}.json"
    if not path.exists():
        pytest.skip(f"{name} not fetched")
    rows = json.loads(path.read_text(encoding="utf-8"))
    assert len(rows) > least
    assert {"original", "correct"} <= set(rows[0]), "the two-column shape changed"
    differing = [r for r in rows if r["original"] != r["correct"]]
    assert len(differing) / len(rows) > 0.9


class TestSourceLicensing:
    """A public request never reaches owner-only material (filtered on the source's
    licence).
    """

    def _db(self, tmp_path):
        conn = connect(tmp_path / "c.db")
        register(conn)
        return conn

    def test_copyrighted_sources_are_marked_owner_only(self, tmp_path):
        conn = self._db(tmp_path)
        restricted = {
            r["id"] for r in conn.execute(
                "SELECT id FROM sources WHERE redistributable = 0"
            )
        }
        # These carry someone else's copyright and must never be public.
        assert {"harno", "eis", "err-r4", "err-lihtsad"} <= restricted

    def test_public_query_excludes_owner_only_items(self, tmp_path):
        conn = self._db(tmp_path)
        add_items(conn, [
            Item("harno", "kuulamine", title="B1 listening", level="B1"),
            Item("generated", "grammatika", body="Ma ostsin pileti ära.", level="A2"),
        ])
        assert len(query(conn)) == 2
        public = query(conn, public_only=True)
        assert len(public) == 1
        assert all(r["redistributable"] for r in public)
        assert "harno" not in {r["source_id"] for r in public}

    def test_unregistered_source_is_rejected(self, tmp_path):
        """Adding material forces an explicit licence decision."""
        conn = self._db(tmp_path)
        with pytest.raises(ValueError, match="unregistered source"):
            add_items(conn, [Item("some-random-blog", "lugemine", body="...")])

    def test_every_registered_source_declares_a_licence(self):
        assert all(s.licence.strip() for s in REGISTRY)


class TestEvalScoreValidity:
    """A run that never reached the model reports no score."""

    def _run_with(self, monkeypatch, side_effect):
        import eesti.evals.gec as gec

        monkeypatch.setattr(gec, "complete", side_effect)
        return gec.run("openrouter", verbose=False)

    def test_all_calls_failing_reports_no_score(self, monkeypatch):
        def rate_limited(*_a, **_k):
            raise RuntimeError("HTTP Error 429: Too Many Requests")

        result = self._run_with(monkeypatch, rate_limited)
        assert result["valid"] is False
        assert result["recall"] is None and result["precision"] is None
        assert "never reached the model" in result["invalid_reason"]

    def test_a_silent_model_scores_zero_recall_not_perfect_precision(self, monkeypatch):
        """A model that answers "no errors" to everything is scored, and fails recall."""
        result = self._run_with(monkeypatch, lambda *_a, **_k: '{"corrections":[]}')
        assert result["valid"] is True
        assert result["recall"] == 0.0
        assert result["precision"] == 1.0
        assert result["broken"] == 0
