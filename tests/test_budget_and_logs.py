"""A day's allowance per lane, and logs that never carry what the learner wrote."""

from __future__ import annotations

import json
import logging

import pytest

from eesti import logs
from eesti.providers import budget


@pytest.fixture
def store(tmp_path):
    import sqlite3

    conn = sqlite3.connect(tmp_path / "p.db")
    budget.bind(conn)
    yield conn
    budget.bind(None)


class TestTheDaysAllowance:
    def test_a_lane_with_a_cap_runs_out(self, store):
        for _ in range(budget.CAPS["llm:openrouter"]):
            assert not budget.exhausted("llm:openrouter")
            budget.spend("llm:openrouter")
        assert budget.exhausted("llm:openrouter")
        assert budget.left("llm:openrouter") == 0

    def test_the_cap_is_under_the_providers_own_limit(self):
        """OpenRouter counts failures against 50 a day, so 50 is not the cap."""
        assert budget.CAPS["llm:openrouter"] < 50

    def test_an_uncapped_lane_is_never_exhausted(self, store):
        for _ in range(50):
            budget.spend("llm:local")
        assert budget.left("llm:local") is None and not budget.exhausted("llm:local")

    def test_counting_survives_a_restart(self, store, tmp_path):
        import sqlite3

        budget.spend("llm:nvidia", 5)
        budget.bind(sqlite3.connect(tmp_path / "p.db"))     # a new process
        assert budget.spent("llm:nvidia") == 5

    def test_yesterdays_calls_do_not_count(self, store):
        store.execute("INSERT INTO budget (day, lane, calls) VALUES ('2020-01-01','llm:nvidia',999)")
        store.commit()
        assert budget.spent("llm:nvidia") == 0

    def test_an_unbound_budget_still_answers(self):
        budget.bind(None)
        assert budget.spent("llm:nvidia") == 0 and not budget.exhausted("llm:nvidia")
        budget.spend("llm:nvidia")               # must not raise

    def test_a_spent_lane_is_skipped_and_the_next_one_answers(self, store, monkeypatch):
        from eesti.providers import grammar

        class Lane:
            def __init__(self, name): self.name = name
            def available(self): return True
            def check(self, text):
                return grammar.GrammarResult(self.name, [])

        monkeypatch.setitem(budget.CAPS, "first", 1)
        budget.spend("first")
        got = grammar.check("Ma elan siin.", providers=[Lane("first"), Lane("second")])
        assert got.engine == "second"
        assert "day's budget spent" in got.diagnostics


class TestTheLogLines:
    def test_a_line_is_json_with_its_fields(self, caplog):
        logs.setup()
        line = logs.JsonLines().format(logging.LogRecord(
            "eesti", logging.INFO, __file__, 1, "request", (), None))
        assert json.loads(line)["msg"] == "request"

    def test_learner_content_is_dropped_not_trusted(self, caplog):
        logs.setup()
        with caplog.at_level(logging.INFO, logger=logs.LOGGER):
            logs.event("check", path="/api/check", text="Ma elan Tallinnas",
                       transcript="ma ütlesin midagi", status=200)
        fields = caplog.records[-1].fields
        assert fields == {"path": "/api/check", "status": 200}

    def test_the_request_line_carries_no_body(self, caplog):
        pytest.importorskip("httpx2")
        from fastapi.testclient import TestClient

        from eesti.app import app

        with caplog.at_level(logging.INFO, logger=logs.LOGGER):
            TestClient(app).get("/api/health")
        line = next(r for r in caplog.records if r.getMessage() == "request")
        assert line.fields["path"] == "/api/health" and line.fields["status"] == 200
        assert "ms" in line.fields and set(line.fields) <= {
            "path", "method", "status", "ms", "request_id", "boot"}
