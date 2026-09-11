"""Fetching the benchmark datasets, and the gate that depends on one of them.

Written after a green CI run that had silently stopped checking Vabamorf.

Adding `grammar_et`'s train split took the fetch from 14 requests to 94, two
test legs run it in parallel on every push, and the HuggingFace datasets server
answered **429 Too Many Requests**. Three things then lined up:

* 429 was not retried — the retry loop re-raised anything under 500, and a rate
  limit is the most retryable status there is;
* one failure ended the whole command, although `inflection_et` had already
  downloaded and was sitting on disk;
* the workflow step is `continue-on-error`, so the morphology gate was skipped
  and the run reported success.

A check that reads green because it never ran is this project's most-repeated
defect. These are the three seams, one test class each.
"""

from __future__ import annotations

import json
import urllib.error
from pathlib import Path

import pytest

from eesti.evals import fetch as fetch_mod

ROOT = Path(__file__).resolve().parents[1]


def _http_error(code: int, headers: dict | None = None):
    return urllib.error.HTTPError(
        "https://example.invalid", code, "nope", headers or {}, None)


class _Server:
    """A datasets server that fails a given number of times, then answers."""

    def __init__(self, failures: list, rows: int = 1):
        self.failures = list(failures)
        self.rows = rows
        self.calls = 0

    def __call__(self, url, timeout=None):
        self.calls += 1
        if self.failures:
            raise self.failures.pop(0)
        return self

    def __enter__(self): return self
    def __exit__(self, *a): return False

    def read(self):
        rows = [{"row": {"original": "a b", "correct": "b a"}}] * self.rows
        self.rows = 0          # second page is empty, so the fetch stops
        return json.dumps({"rows": rows}).encode()


class TestARateLimitIsRetried:
    def test_429_is_not_a_permanent_failure(self, tmp_path, monkeypatch):
        """It says "later", not "no". Re-raising it is what skipped the gate."""
        server = _Server([_http_error(429), _http_error(429)])
        monkeypatch.setattr(fetch_mod.urllib.request, "urlopen", server)
        monkeypatch.setattr(fetch_mod.time, "sleep", lambda _: None)

        out = fetch_mod.fetch("grammar_et", "train", 10, tmp_path, key="k")
        assert json.loads(out.read_text())
        assert not server.failures, "both rate limits were waited out"
        assert server.calls >= 3

    def test_a_404_still_fails_immediately(self, tmp_path, monkeypatch):
        """Asking wrongly is not worth four attempts."""
        server = _Server([_http_error(404)] * 6)
        monkeypatch.setattr(fetch_mod.urllib.request, "urlopen", server)
        monkeypatch.setattr(fetch_mod.time, "sleep", lambda _: None)

        with pytest.raises(urllib.error.HTTPError):
            fetch_mod.fetch("nope", "train", 10, tmp_path)
        assert server.calls == 1

    def test_a_rate_limit_that_never_lifts_is_still_an_error(
        self, tmp_path, monkeypatch
    ):
        server = _Server([_http_error(429)] * 10)
        monkeypatch.setattr(fetch_mod.urllib.request, "urlopen", server)
        monkeypatch.setattr(fetch_mod.time, "sleep", lambda _: None)

        with pytest.raises(urllib.error.HTTPError):
            fetch_mod.fetch("grammar_et", "train", 10, tmp_path)
        assert server.calls == fetch_mod.RETRIES

    def test_the_servers_own_retry_after_wins(self):
        """It has said how long to wait. Guessing is both ruder and slower."""
        exc = _http_error(429, {"Retry-After": "12"})
        assert fetch_mod._backoff(exc, 0) == 12

    def test_but_not_past_the_cap(self):
        """A header asking for an hour is not something a build honours."""
        exc = _http_error(429, {"Retry-After": "3600"})
        assert fetch_mod._backoff(exc, 0) == fetch_mod.RETRY_AFTER_CAP

    def test_a_missing_or_junk_header_falls_back_to_our_own_backoff(self):
        assert fetch_mod._backoff(_http_error(429), 3) == 8
        assert fetch_mod._backoff(_http_error(429, {"Retry-After": "soon"}), 3) == 8


class TestOneFailureDoesNotTakeTheRestDown:
    @pytest.fixture
    def only_grammar2_fails(self, monkeypatch, tmp_path):
        def fake(name, split, total, out_dir=None, key=None):
            if key == "grammar2_et":
                raise urllib.error.HTTPError("u", 429, "rate", {}, None)
            path = Path(out_dir) / f"{key or name}.json"
            path.write_text(json.dumps([{"original": "a", "correct": "a"}]))
            return path

        monkeypatch.setattr(fetch_mod, "fetch", fake)
        return tmp_path

    def test_the_others_still_arrive(self, only_grammar2_fails):
        counts, failures = fetch_mod.fetch_all(only_grammar2_fails)
        assert set(failures) == {"grammar2_et"}
        assert "inflection_et" in counts, "the file the morphology gate needs"
        assert "grammar_et" in counts, "and the eval track's"

    def test_the_gates_dataset_is_required_and_the_pools_are_not(self):
        assert fetch_mod.REQUIRED == {"inflection_et", "grammar_et"}
        assert "grammar_et_train" not in fetch_mod.REQUIRED
        assert "grammar2_et" not in fetch_mod.REQUIRED

    def test_required_only_asks_for_nothing_else(self, only_grammar2_fails):
        """Nothing in CI reads the word-order pools, and asking someone else's
        server for 7 937 rows nobody opens is what earned the 429."""
        counts, failures = fetch_mod.fetch_all(only_grammar2_fails,
                                               required_only=True)
        assert set(counts) == fetch_mod.REQUIRED
        assert not failures


class TestTheCommandFailsOnWhatMatters:
    def _run(self, monkeypatch, failures, required_only=False):
        import argparse

        from eesti.cli.build import cmd_fetch_bench

        monkeypatch.setattr(
            fetch_mod, "fetch_all",
            lambda *a, **k: ({"inflection_et": 1400}, failures))
        return cmd_fetch_bench(argparse.Namespace(required_only=required_only))

    def test_an_optional_pool_failing_is_not_an_error(self, monkeypatch):
        """Fewer pairs is fewer word-order items, which that module already
        treats as ordinary. Failing here is what skipped the gate."""
        assert self._run(monkeypatch, {"grammar2_et": "429"}) == 0

    def test_a_required_dataset_failing_is(self, monkeypatch):
        assert self._run(monkeypatch, {"inflection_et": "429"}) == 1


class TestTheWorkflowAsksForWhatItReads:
    def test_ci_does_not_fetch_the_word_order_pools(self):
        body = (ROOT / ".github" / "workflows" / "tests.yml").read_text(
            encoding="utf-8")
        assert "fetch-bench --required-only" in body

    def test_and_the_gate_still_runs_only_when_the_fetch_worked(self):
        """`continue-on-error` on the fetch is deliberate — a third party's bad
        minute must not fail the suite — which is exactly why the skip has to
        stay loud."""
        body = (ROOT / ".github" / "workflows" / "tests.yml").read_text(
            encoding="utf-8")
        assert "steps.bench.outcome == 'success'" in body
        assert "::warning title=Validation skipped" in body
