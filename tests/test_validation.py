"""Foundation checks against third-party data.

Everything this app produces — drills, the reverse index, the exported dataset —
inherits Vabamorf's correctness. These tests check that inheritance against data
this project did not write.

Skipped when the benchmark files are absent, so the suite still runs offline for
someone who has not fetched them.
"""

import json

import pytest

from eesti.evals.morphology import DATASET, run
from eesti.sources import REGISTRY, Item, add_items, connect, query, register

pytestmark = pytest.mark.skipif(
    not DATASET.exists(), reason="run `python -m eesti.cli fetch-bench` first"
)


def test_vabamorf_agrees_with_native_gold_forms():
    """Vabamorf must match TalTech's native-curated inflections.

    Threshold is 95%, below the measured 98.1%, so a real regression trips it
    while the known invariant-adjective disagreements do not.
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


def test_grammar_benchmark_is_wellformed():
    """grammar_et pairs must actually differ, or they test nothing."""
    path = DATASET.parent / "grammar_et.json"
    if not path.exists():
        pytest.skip("grammar_et not fetched")
    rows = json.loads(path.read_text(encoding="utf-8"))
    assert len(rows) > 500
    differing = [r for r in rows if r["original"] != r["correct"]]
    assert len(differing) / len(rows) > 0.9


class TestSourceLicensing:
    """A public request must never be able to reach owner-only material.

    This is the guard that makes serving HARNO exam material legitimate: fine to
    study from privately, not fine to republish. The filter is on the source's
    licence, so a new source cannot leak by forgetting to tag its items.
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
