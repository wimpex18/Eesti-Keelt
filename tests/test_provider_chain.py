"""The fallback chain: a failing provider falls through quickly, the engine that
answered is named, and a dead provider is skipped by the breaker.

Research inference endpoints are often down together, so every provider is
optional enrichment. TartuNLP's failure mode is a ~60 s gateway timeout, so
`PROVIDER_TIMEOUT` is 5 s and the chain must fall back within 6 s.
"""

from __future__ import annotations

import io
import urllib.error

import pytest

from eesti.config import PROVIDER_TIMEOUT
from eesti.providers import breaker, grammar
from eesti.providers.grammar import Correction, GrammarResult, check


@pytest.fixture(autouse=True)
def clean_breaker():
    """Reset the breaker around each test: it is keyed by provider name and outlives a
    call, so tests would otherwise depend on order.
    """
    breaker.reset()
    yield
    breaker.reset()


class Provider:
    """A stand-in with a scripted outcome."""

    def __init__(self, name, *, up=True, fails=None, answer=None):
        self.name = name
        self._up = up
        self._fails = fails
        self._answer = answer
        self.called = False

    def available(self):
        return self._up

    def check(self, text):
        self.called = True
        if self._fails:
            raise self._fails
        return GrammarResult(self.name, self._answer or [])


def a_500():
    return urllib.error.HTTPError("https://api.tartunlp.ai/grammar/v2", 500,
                                  "Internal Server Error", {}, None)


class TestFallback:
    def test_a_500_falls_through_to_the_next_provider(self):
        dead = Provider("tartunlp", fails=a_500())
        alive = Provider("llm", answer=[Correction("raamatut", "raamatu",
                                                   "obj-case", "почему")])
        got = check("Ma lugesin raamatut läbi", [dead, alive])
        assert got.engine == "llm"
        assert alive.called

    def test_the_engine_that_answered_is_named(self):
        """Shown in the UI as-is: which engine replied changes how much the
        learner should trust the correction."""
        got = check("tekst", [Provider("llm", answer=[])])
        assert got.engine == "llm"

    def test_what_was_skipped_is_recorded(self):
        """Silent fallback hides an outage for weeks."""
        got = check("tekst", [Provider("tartunlp", fails=a_500()),
                              Provider("llm", answer=[])])
        assert "tartunlp" in got.diagnostics

    def test_the_note_carries_the_status_code_not_just_the_type(self):
        """The note carries the status code: 429 (wait), 401 (replace the key) and 502 (the
        provider's bad minute) need different actions.
        """
        for code in (401, 429, 502):
            # The breaker opens after two failures on one name, so without
            # this the third code is skipped rather than called.
            breaker.reset()
            got = check("tekst", [
                Provider("llm:openrouter", fails=urllib.error.HTTPError(
                    "https://openrouter.ai/api/v1/chat/completions", code,
                    "boom", {}, None)),
                Provider("vabamorf-offline", answer=[]),
            ])
            assert f"llm:openrouter: HTTPError {code}" in got.diagnostics

    def test_the_note_never_carries_a_response_body(self):
        """It is printed into CI logs. A provider that echoes the request on
        error would put the learner's own sentence there."""
        body = io.BytesIO(b"secret-ish: the learner's sentence")
        got = check("Ma lugesin raamatut labi", [
            Provider("llm:openrouter", fails=urllib.error.HTTPError(
                "https://openrouter.ai/api/v1/chat/completions", 400,
                "Bad Request", {}, body)),
            Provider("vabamorf-offline", answer=[]),
        ])
        assert "secret-ish" not in got.diagnostics
        assert "raamatut" not in got.diagnostics

    def test_a_failure_with_no_code_still_names_its_type(self):
        """URLError and TimeoutError have no status; the type is all there is."""
        got = check("tekst", [Provider("tartunlp", fails=TimeoutError()),
                              Provider("llm", answer=[])])
        assert "tartunlp: TimeoutError" in got.diagnostics

    def test_an_unavailable_provider_is_never_called(self):
        """`available()` is the cheap check; calling anyway costs the timeout."""
        off = Provider("tartunlp", up=False)
        check("tekst", [off, Provider("llm", answer=[])])
        assert not off.called

    def test_every_provider_failing_is_degraded_not_an_exception(self):
        """A study session survives every provider failing."""
        got = check("tekst", [Provider("a", fails=a_500()),
                              Provider("b", fails=OSError("no route"))])
        assert got.degraded is True
        assert got.corrections == []

    def test_a_provider_returning_nonsense_is_caught_too(self):
        """Bad JSON and SDK errors are caught per provider, like network errors."""
        got = check("tekst", [Provider("a", fails=ValueError("bad json")),
                              Provider("b", answer=[])])
        assert got.engine == "b"

    def test_the_first_healthy_provider_wins_and_the_rest_are_spared(self):
        first = Provider("a", answer=[])
        second = Provider("b", answer=[])
        assert check("tekst", [first, second]).engine == "a"
        assert not second.called


class TestTheBreaker:
    """Failures are remembered by name, so a dead service is stepped over."""

    def test_a_provider_that_just_failed_is_skipped(self):
        for _ in range(5):
            check("tekst", [Provider("tartunlp", fails=a_500()),
                            Provider("llm", answer=[])])
        dead = Provider("tartunlp", fails=a_500())
        got = check("tekst", [dead, Provider("llm", answer=[])])
        assert not dead.called, "the breaker should have stepped over it"
        assert got.engine == "llm"

    def test_the_skip_is_visible_in_the_note(self):
        for _ in range(5):
            check("tekst", [Provider("tartunlp", fails=a_500()),
                            Provider("llm", answer=[])])
        got = check("tekst", [Provider("tartunlp", fails=a_500()),
                              Provider("llm", answer=[])])
        assert "skipped" in got.diagnostics


class TestTiming:
    def test_the_timeout_is_short_enough_to_fall_back_inside_six_seconds(self):
        """The observed TartuNLP failure is a ~60 s timeout; the chain must not wait it out."""
        assert PROVIDER_TIMEOUT <= 5.0

    def test_the_whole_chain_returns_promptly_when_everything_fails(self):
        import time

        started = time.monotonic()
        check("tekst", [Provider("a", fails=a_500()),
                        Provider("b", fails=a_500())])
        assert time.monotonic() - started < 1.0


class TestTheBreakerSurvivesTheProcess:
    """The breaker persists its state, so a cold container does not pay a dead
    provider's timeout again.
    """

    class Dead:
        name = "tartunlp"

        def __init__(self, calls):
            self.calls = calls

        def available(self):
            return True

        def check(self, text):
            self.calls.append(1)
            raise TimeoutError("as production reports on every run")

    class Fallback:
        name = "vabamorf-offline"

        def available(self):
            return True

        def check(self, text):
            from eesti.providers.grammar import GrammarResult

            return GrammarResult("vabamorf-offline", [], degraded=True)

    def cold_start(self, conn):
        """What a new container does: fresh process memory, same database."""
        breaker._failures.clear()
        breaker._loaded = False
        breaker.bind(conn)

    @pytest.fixture
    def store(self, tmp_path):
        from eesti.progress import connect

        conn = connect(tmp_path / "p.db")
        breaker.bind(conn)
        breaker.reset()
        yield conn
        breaker.bind(None)
        breaker.reset()

    def test_a_dead_provider_is_tried_twice_ever_not_twice_per_start(self, store):
        calls = []
        for _ in range(6):
            self.cold_start(store)
            check("Ma lugesin raamatut läbi.",
                  providers=[self.Dead(calls), self.Fallback()])
        assert len(calls) == breaker.THRESHOLD, (
            f"tried {len(calls)} times across 6 cold starts; the breaker is "
            f"not surviving the process"
        )

    def test_without_a_store_it_forgets_as_it_always_did(self, tmp_path):
        """Unbound (in-memory) remains supported — the CLI runs that way."""
        breaker.bind(None)
        breaker.reset()
        calls = []
        for _ in range(3):
            breaker._failures.clear()
            check("Ma lugesin raamatut läbi.",
                  providers=[self.Dead(calls), self.Fallback()])
        assert len(calls) == 3

    def test_the_timestamp_means_something_to_the_next_process(self, store):
        """`monotonic` is meaningless across processes — it would have made a
        restored breaker either permanently open or permanently closed
        depending on which way the clocks happened to fall."""
        import time

        breaker.record_failure("tartunlp")
        last = store.execute(
            "SELECT last FROM breaker WHERE name = 'tartunlp'").fetchone()[0]
        assert abs(last - time.time()) < 5

    def test_a_success_clears_it_everywhere(self, store):
        for _ in range(3):
            breaker.record_failure("tartunlp")
        assert breaker.is_open("tartunlp")
        breaker.record_success("tartunlp")
        self.cold_start(store)
        assert not breaker.is_open("tartunlp")

    def test_the_cooldown_grows_but_stops_at_about_a_week(self):
        """The cooldown stops growing at about a week."""
        assert breaker.cooldown(breaker.THRESHOLD) == breaker.COOLDOWN
        assert breaker.cooldown(breaker.THRESHOLD + 1) == breaker.COOLDOWN * 2
        assert breaker.cooldown(99) == breaker.MAX_COOLDOWN
        assert breaker.MAX_COOLDOWN <= 7 * 24 * 3600

    def test_below_the_threshold_nothing_is_skipped(self):
        assert breaker.cooldown(breaker.THRESHOLD - 1) == 0.0

    def test_an_unwritable_store_still_breaks_the_circuit(self, tmp_path):
        """Storage is an optimisation over forgetting, never a dependency."""
        from eesti.progress import connect

        conn = connect(tmp_path / "p.db")
        breaker.bind(conn)
        breaker.reset()
        conn.close()                       # every write from here raises
        for _ in range(breaker.THRESHOLD):
            breaker.record_failure("tartunlp")
        assert breaker.is_open("tartunlp")
        breaker.bind(None)


class TestWhatTheNoteSays:
    """The diagnostics name the provider's own error code, never a response body (the
    note reaches CI logs; the checked text is the learner's writing).
    """

    @staticmethod
    def _http(code: int, body: bytes | None):
        return urllib.error.HTTPError(
            "https://integrate.api.nvidia.com/v1/chat/completions", code, "Forbidden",
            {}, io.BytesIO(body) if body is not None else None)

    def test_the_providers_own_error_name_reaches_the_note(self):
        """A valid key with a withdrawn model: the provider's code says so."""
        exc = self._http(403, b'{"error":{"code":"model_decommissioned",'
                              b'"message":"llama-3.3-70b-versatile has been '
                              b'decommissioned"}}')
        assert grammar.why_failed(exc) == "HTTPError 403 (model_decommissioned)"

    def test_type_is_read_when_there_is_no_code(self):
        """Providers disagree about which field carries the identifier."""
        exc = self._http(401, b'{"error":{"type":"invalid_api_key"}}')
        assert grammar.why_failed(exc) == "HTTPError 401 (invalid_api_key)"

    def test_the_learners_sentence_cannot_reach_the_note(self):
        """A body that is prose (spaces, capitals, non-ASCII) is not an identifier: the note
        says `no-code` and repeats none of it.
        """
        exc = self._http(400, '{"error":{"code":"Ma lugesin raamatut läbi.",'
                              '"message":"Ma lugesin raamatut läbi."}}'
                              .encode())
        note = grammar.why_failed(exc)
        assert note == "HTTPError 400 (no-code)"
        assert "raamat" not in note and "lugesin" not in note

    def test_html_from_a_proxy_is_named_as_such_not_quoted(self):
        """A proxy's HTML 403 is reported as `non-json`, distinct from a provider refusal,
        without repeating the page.
        """
        exc = self._http(403, b"<!DOCTYPE html><title>Attention Required</title>")
        note = grammar.why_failed(exc)
        assert note == "HTTPError 403 (non-json)"
        assert "html" not in note.lower() and "Attention" not in note

    def test_no_body_at_all_still_names_the_status(self):
        """`fp` is None on a synthesised error and on some proxies. Explaining a
        failure must never fail."""
        assert grammar.why_failed(self._http(500, None)) == "HTTPError 500"

    def test_a_non_http_failure_is_unchanged(self):
        assert grammar.why_failed(TimeoutError()) == "TimeoutError"

    def test_the_note_carries_it_through_the_chain(self):
        """The unit above is only useful if `check` still puts it in the note —
        this project has shipped a correct function nothing called."""
        exc = self._http(403, b'{"error":{"code":"model_decommissioned"}}')
        got = check("tekst", [Provider("llm:nvidia", fails=exc),
                              Provider("vabamorf", answer=[])])
        assert "llm:nvidia: HTTPError 403 (model_decommissioned)" in got.diagnostics


class TestImportingTheAppBindsTheBreaker:
    """Importing the app binds the breaker to durable storage.

    Checked in a subprocess, because `conftest` deliberately unbinds the breaker for
    in-process tests.
    """

    @staticmethod
    def _ask(expression: str) -> str:
        import subprocess
        import sys
        from pathlib import Path

        code = ("from eesti import app  # noqa: F401\n"
                "from eesti.providers import breaker\n"
                f"print({expression})\n")
        done = subprocess.run(
            [sys.executable, "-c", code], capture_output=True, text=True,
            cwd=Path(__file__).resolve().parents[1])
        assert done.returncode == 0, done.stderr[-2000:]
        return done.stdout.strip()

    def test_an_opener_is_registered(self):
        assert self._ask("breaker._opener is not None") == "True"

    def test_it_is_the_learners_progress_database(self):
        """`progress.db` rather than a file of its own, so the breaker's state
        rides the existing state snapshot across a cold start."""
        assert self._ask("breaker._opener.__name__") == "progress_db"

    def test_no_connection_is_opened_at_import(self):
        """Registering an opener is what makes binding at import safe: a
        connection here would resolve the path at import, which is the habit
        this project has paid for three times."""
        assert self._ask("breaker._store is None") == "True"


class TestTheEvalSaysWhyItCouldNotMeasure:
    """An eval that reaches nothing must still name the reason, via
    `grammar.why_failed`, not `type(exc).__name__`.
    """

    @staticmethod
    def _http(code, body):
        import io
        import json
        import urllib.error

        raw = json.dumps(body).encode() if body is not None else b""
        return urllib.error.HTTPError(
            "https://openrouter.ai/api/v1/chat/completions", code,
            "Bad Request", {}, io.BytesIO(raw))

    def test_the_renderer_names_a_400s_cause(self):
        from eesti.providers import grammar

        exc = self._http(400, {"error": {"code": "json_mode_unsupported"}})
        assert grammar.why_failed(exc) == "HTTPError 400 (json_mode_unsupported)"

    def test_both_eval_tracks_use_it(self):
        """Both eval tracks render failures through `why_failed`."""
        import inspect

        from eesti.evals import external, gec

        for module in (gec, external):
            source = inspect.getsource(module)
            # Comments stripped before searching, so prose about the old rendering does not
            # match.
            code = "\n".join(line.split("#")[0] for line in source.splitlines())
            assert "why_failed(exc)" in code, module.__name__
            assert "type(exc).__name__" not in code, (
                f"{module.__name__} still renders the exception class and "
                f"drops the provider's reason")


class TestTheEvalScoresThePromptTheAppShips:
    """The eval scores the prompt the app ships: `evals/gec.py` imports it rather than
    keeping a copy.
    """

    def test_the_eval_imports_it_rather_than_restating_it(self):
        from eesti.evals import gec
        from eesti.providers import grammar

        assert gec.SYSTEM is grammar.SYSTEM_PROMPT

    def test_no_second_prompt_is_defined_alongside_it(self):
        """The failure this replaces: a copy appears, nobody notices, and the
        eval quietly measures something else again."""
        import inspect

        from eesti.evals import external, gec

        for module in (gec, external):
            source = inspect.getsource(module)
            code = "\n".join(line.split("#")[0] for line in source.splitlines())
            assert 'SYSTEM = """' not in code, (
                f"{module.__name__} defines its own prompt again")

    def test_the_scorer_ignores_the_field_the_eval_does_not_need(self):
        """The shipped contract has a Russian `why` the eval has no use for.
        It is read past, not stripped -- an eval that rewrote the contract
        would be measuring a third prompt."""
        from eesti.evals.gec import _flagged

        result = {"corrections": [
            {"wrong": "raamatut", "correct": "raamatu", "tag": "obj-case",
             "why": "Здесь нужен omastav."}]}
        assert _flagged(result, "raamatut")


class TestTheLearnerReadsRussianAndTheOperatorReadsTheTrail:
    """The learner's note is Russian and never contains the operator's failure trail;
    the trail goes to `diagnostics`.
    """

    def test_the_trail_is_not_in_the_note(self, monkeypatch):
        from eesti.providers import grammar

        class Down:
            name = "llm:test"
            def available(self): return True
            def check(self, text): raise TimeoutError()

        monkeypatch.setattr(grammar, "_breaker_open", lambda name: False)
        monkeypatch.setattr(grammar, "_record_failure", lambda name: None)
        got = grammar.check("Ma lugesin raamatu.", providers=[Down(), grammar.VabamorfFallback()])
        assert "llm:test" in got.diagnostics
        assert "skipped" not in got.note and "Error" not in got.note

    def test_with_keys_set_the_note_does_not_ask_for_a_key(self, monkeypatch):
        from eesti.providers import grammar

        monkeypatch.setenv("OPENROUTER_API_KEY", "set-but-failing")
        assert "задай ключ" not in grammar._offline_note()
        assert "не ответили" in grammar._offline_note()

    def test_without_keys_it_still_says_which_to_set(self, monkeypatch):
        from eesti.providers import grammar

        for k in grammar.EXPLAINING_KEYS:
            monkeypatch.delenv(k, raising=False)
        assert "OPENROUTER_API_KEY" in grammar._offline_note()

    def test_the_api_carries_both(self):
        from eesti.providers.grammar import GrammarResult

        got = GrammarResult("x", note="n", diagnostics="d").to_dict()
        assert (got["note"], got["diagnostics"]) == ("n", "d")


class TestNeurotolgeCorrection:
    """Neurotõlge run est→est corrects, but also paraphrases; only edits code can
    vouch for survive (`NeurotolgeCorrection.verified`).
    """

    @pytest.fixture
    def lane(self):
        pytest.importorskip("estnltk")
        from eesti.providers.grammar import NeurotolgeCorrection

        return NeurotolgeCorrection()

    def test_a_form_change_of_the_same_word_is_kept(self, lane):
        got = lane.verified("Mul on kaks koer.", "Mul on kaks koera.")
        assert [(c.wrong, c.correct) for c in got] == [("koer", "koera")]

    def test_a_negated_object_may_become_partitive(self, lane):
        got = lane.verified("Ma ei ostnud pileti.", "Ma ei ostnud piletit.")
        assert [(c.wrong, c.correct, c.tag) for c in got] == [
            ("pileti", "piletit", "obj-case")]

    def test_an_aspect_rewrite_is_not_trusted(self, lane):
        """`uut autot` is correct Estonian (ongoing); Neurotõlge prefers `uue auto`."""
        assert lane.verified("Ma ostsin uut autot.", "Ma ostsin uue auto.") == []

    def test_dropped_and_reordered_words_are_not_corrections(self, lane):
        assert lane.verified("Lugesin raamatut läbi eile.", "Lugesin eile raamatut.") == []

    def test_a_number_change_is_a_paraphrase(self, lane):
        assert lane.verified("Eile tegin kodutööd.", "Eile tegin kodutöid.") == []

    def test_it_sits_after_the_explaining_lanes(self):
        from eesti.providers import grammar

        names = [p.name for p in grammar.build_chain()]
        assert names.index("tartunlp-mt") > max(
            names.index(f"llm:{n}") for n in grammar.LLM_PREFERENCE)
        assert names[-1] == "vabamorf-offline" and names.index("tartunlp") > names.index("llm:workers-ai")


def test_breaker_failures_survive_requests_on_different_threads(tmp_path):
    """A dead provider must not cost its timeout again after a cold start."""
    import concurrent.futures
    from eesti.progress import connect
    path = tmp_path / 'threaded.db'
    breaker.bind_later(lambda: connect(path))
    breaker._failures.clear()
    try:
        breaker.record_failure('threaded')  # opens in this thread
        with concurrent.futures.ThreadPoolExecutor(1) as pool:
            pool.submit(breaker.record_failure, 'threaded').result()
        breaker._failures.clear()          # a new process must see both
        breaker.bind_later(lambda: connect(path))
        assert breaker.is_open('threaded')
    finally:
        breaker.bind(None)
        breaker.reset()
