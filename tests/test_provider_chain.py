"""The fallback chain, which is the whole reason this app has providers at all.

The research that started this project probed four inference endpoints at two
universities and found **all four returning 500 simultaneously**, while every
static dataset answered perfectly. That is not bad luck, it is the operating
reality of grant-funded infrastructure, and it produced the rule the
architecture is built on: own your data, treat every research API as optional
enrichment that may be gone on exam eve.

The plan asked for one check in particular — *"expect a 500, assert the chain
falls back in <6 s and labels the engine"* — and it was never written. These
are that check, without needing anyone's server to be down today.

Timing matters as much as the fallback. TartuNLP's observed failure is a **61-
second gateway timeout**, and a lesson that stalls for a minute is a lesson
abandoned; `PROVIDER_TIMEOUT` is 5 s for exactly that reason.
"""

from __future__ import annotations

import io
import io
import urllib.error

import pytest

from eesti.config import PROVIDER_TIMEOUT
from eesti.providers import breaker, grammar
from eesti.providers.grammar import Correction, GrammarResult, check


@pytest.fixture(autouse=True)
def clean_breaker():
    """The circuit breaker is keyed by provider *name* and outlives a call.

    That is deliberate in production — the whole point is to stop paying a
    timeout for a service that failed twice a minute ago — and it makes tests
    order-dependent: a provider called "a" that failed in one test is skipped
    in the next. Reset around each test rather than inventing unique names,
    because the shared state is the thing being relied on.
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
        assert "tartunlp" in got.note

    def test_the_note_carries_the_status_code_not_just_the_type(self):
        """A live deployment reported `llm:openrouter: HTTPError` and the note
        could not say which one. 429 means the free tier is spent and it will
        work again tomorrow; 401 means the key is dead and study is broken
        until it is replaced; 502 is the provider's bad minute. One word for
        three different jobs."""
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
            assert f"llm:openrouter: HTTPError {code}" in got.note

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
        assert "secret-ish" not in got.note
        assert "raamatut" not in got.note

    def test_a_failure_with_no_code_still_names_its_type(self):
        """URLError and TimeoutError have no status; the type is all there is."""
        got = check("tekst", [Provider("tartunlp", fails=TimeoutError()),
                              Provider("llm", answer=[])])
        assert "tartunlp: TimeoutError" in got.note

    def test_an_unavailable_provider_is_never_called(self):
        """`available()` is the cheap check; calling anyway costs the timeout."""
        off = Provider("tartunlp", up=False)
        check("tekst", [off, Provider("llm", answer=[])])
        assert not off.called

    def test_every_provider_failing_is_degraded_not_an_exception(self):
        """A study session must survive the whole internet being unhelpful."""
        got = check("tekst", [Provider("a", fails=a_500()),
                              Provider("b", fails=OSError("no route"))])
        assert got.degraded is True
        assert got.corrections == []

    def test_a_provider_returning_nonsense_is_caught_too(self):
        """Not only network errors: bad JSON and SDK bugs are equally fatal to
        one provider and equally survivable for the chain."""
        got = check("tekst", [Provider("a", fails=ValueError("bad json")),
                              Provider("b", answer=[])])
        assert got.engine == "b"

    def test_the_first_healthy_provider_wins_and_the_rest_are_spared(self):
        first = Provider("a", answer=[])
        second = Provider("b", answer=[])
        assert check("tekst", [first, second]).engine == "a"
        assert not second.called


class TestTheBreaker:
    """Failures are remembered by name, so a dead service is stepped over
    rather than waited on once per request."""

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
        assert "skipped" in got.note


class TestTiming:
    def test_the_timeout_is_short_enough_to_fall_back_inside_six_seconds(self):
        """The plan's number. The observed TartuNLP failure is a 61-second
        gateway timeout, and waiting that out is a lesson abandoned."""
        assert PROVIDER_TIMEOUT <= 5.0

    def test_the_whole_chain_returns_promptly_when_everything_fails(self):
        import time

        started = time.monotonic()
        check("tekst", [Provider("a", fails=a_500()),
                        Provider("b", fails=a_500())])
        assert time.monotonic() - started < 1.0


class TestTheBreakerSurvivesTheProcess:
    """The breaker existed to stop a dead provider costing its full timeout on
    every request, and in production it did not do that.

    State was a module-level dict, documented as process-local and "right for a
    single-user app". Cloud Run scales to zero, so a learner who checks one
    paragraph in the evening gets a cold container almost every time — and a
    cold container has an empty breaker. With a threshold of two, the first two
    requests of every container lifetime paid the timeout in full. TartuNLP's
    grammar endpoint has answered 500 after ~61 seconds since the research
    phase and did so again when re-probed, so at a 5 second provider timeout
    that was ten seconds of dead waiting per cold start for a service that has
    never once answered.
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
        """The regression, stated as a test so the fix cannot silently revert.
        Unbound is still a supported mode — the CLI runs that way."""
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
        """The plan's instruction is to re-probe the research APIs weekly, so
        there is nothing to gain from backing off further: a permanently dead
        endpoint should cost one timeout a week, not two a session."""
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
    """The note is the only channel between a failing provider and the operator.

    It has now been widened twice for the same reason. First `HTTPError` alone
    could not distinguish "wait" from "replace the key"; the status code fixed
    that. Then `HTTPError 403` sent a diagnosis at a key that was fine, because
    the real cause was a model id deprecated six days earlier — and the provider
    had named it, in a field the note dropped.

    The constraint that shaped the fix: the note is printed into CI logs, and
    the text being checked is the learner's own writing.
    """

    @staticmethod
    def _http(code: int, body: bytes | None):
        return urllib.error.HTTPError(
            "https://api.groq.com/openai/v1/chat/completions", code, "Forbidden",
            {}, io.BytesIO(body) if body is not None else None)

    def test_the_providers_own_error_name_reaches_the_note(self):
        """The 403 this was written for: valid key, withdrawn model."""
        exc = self._http(403, b'{"error":{"code":"model_decommissioned",'
                              b'"message":"llama-3.3-70b-versatile has been '
                              b'decommissioned"}}')
        assert grammar.why_failed(exc) == "HTTPError 403 (model_decommissioned)"

    def test_type_is_read_when_there_is_no_code(self):
        """Providers disagree about which field carries the identifier."""
        exc = self._http(401, b'{"error":{"type":"invalid_api_key"}}')
        assert grammar.why_failed(exc) == "HTTPError 401 (invalid_api_key)"

    def test_the_learners_sentence_cannot_reach_the_note(self):
        """The whole reason bodies were banned. Prose has spaces, capitals and
        non-ASCII; an identifier has none of them.

        The note says `no-code` rather than nothing, because "the provider gave
        no identifier" and "there was no provider response to read" are
        different facts. What matters here is unchanged and asserted twice
        below: not one character of the sentence survives.
        """
        exc = self._http(400, '{"error":{"code":"Ma lugesin raamatut läbi.",'
                              '"message":"Ma lugesin raamatut läbi."}}'
                              .encode())
        note = grammar.why_failed(exc)
        assert note == "HTTPError 400 (no-code)"
        assert "raamat" not in note and "lugesin" not in note

    def test_html_from_a_proxy_is_named_as_such_not_quoted(self):
        """A proxy 403 is not a provider 403, and knowing which is the whole
        diagnosis: one means fix the request, the other means the request never
        arrived. The body is a whole HTML page, so none of it is repeated —
        only the fact that it was not the provider's JSON."""
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
        got = check("tekst", [Provider("llm:groq", fails=exc),
                              Provider("vabamorf", answer=[])])
        assert "llm:groq: HTTPError 403 (model_decommissioned)" in got.note


class TestThePinnedModels:
    """Rule 1 of `llm.py`: never pin a model id without probing it.

    The rule was written down and then broken by the file that states it. A test
    cannot probe a catalogue without a key, so it checks the one thing it can:
    that no id withdrawn on a date already known is still pinned here.
    """

    def test_no_provider_pins_a_model_known_to_be_withdrawn(self):
        from eesti.providers.llm import PROVIDERS

        # Announced deprecated by Groq for free and developer tiers on
        # 2026-08-16; observed live as HTTPError 403 on 2026-08-22.
        withdrawn = {"llama-3.3-70b-versatile", "llama-3.1-8b-instant"}
        pinned = {p.name: p.default_model for p in PROVIDERS.values()}
        assert not (set(pinned.values()) & withdrawn), pinned


class TestImportingTheAppBindsTheBreaker:
    """The binding is an import-time side effect, and it went missing once.

    `api/deps.py` ends with `_bind_breaker()`. It is a bare expression with no
    name, which is how the tool that split `app.py` into routers dropped it:
    functions, classes and assignments moved, and this did not. Nothing failed.
    The breaker kept working from a module-level dict — and a module-level dict
    is precisely what it was written to stop using, because Cloud Run scales to
    zero and every cold container then pays a dead provider's full timeout
    twice before stepping over it.

    Checked in a subprocess because this suite deliberately unbinds the breaker
    (`conftest`, autouse) so that tests cannot write to the learner's real
    `data/progress.db`. In-process, the state this asserts has already been
    taken apart on purpose.
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
    """An eval that reaches nothing must still name the reason.

    On 2026-09-02 the first `huggingface` run reported, eighteen times:

        ✗ Ma lugesin eile selle raamatut läbi.
            ERROR HTTPError: HTTP Error 400: Bad Request

    and then `18/18 cases never reached the model (rate limit, timeout or
    unparseable reply) — no score reported`. Three guesses, none of them right:
    the token authenticated (a bad one is 401), the quota was untouched (that is
    429), and the reply was never the problem (400 means the request was). The
    provider had named the cause in its body and both eval tracks dropped it,
    rendering `type(exc).__name__`.

    `grammar.why_failed` — then named `_why` — already existed for exactly this,
    and its docstring records the same lesson being learned in the live chain a
    fortnight earlier. It was one import away and nobody had crossed the gap.
    """

    @staticmethod
    def _http(code, body):
        import io
        import json
        import urllib.error

        raw = json.dumps(body).encode() if body is not None else b""
        return urllib.error.HTTPError(
            "https://router.huggingface.co/v1/chat/completions", code,
            "Bad Request", {}, io.BytesIO(raw))

    def test_the_renderer_names_a_400s_cause(self):
        from eesti.providers import grammar

        exc = self._http(400, {"error": {"code": "json_mode_unsupported"}})
        assert grammar.why_failed(exc) == "HTTPError 400 (json_mode_unsupported)"

    def test_both_eval_tracks_use_it(self):
        """Structural, because the failure is invisible until a provider is
        actually failing — which is when nobody wants to discover that the
        message says nothing. Two tracks; the hand one was fixed first and the
        external one is the copy that would have been left behind."""
        import inspect

        from eesti.evals import external, gec

        for module in (gec, external):
            source = inspect.getsource(module)
            # Comments stripped: `gec.py` quotes the old rendering in the
            # comment explaining why it was replaced, and the first version of
            # this assertion matched that. Sixth prose-vs-code match this
            # sprint, and the second where the prose was mine.
            code = "\n".join(line.split("#")[0] for line in source.splitlines())
            assert "why_failed(exc)" in code, module.__name__
            assert "type(exc).__name__" not in code, (
                f"{module.__name__} still renders the exception class and "
                f"drops the provider's reason")


class TestTheEvalScoresThePromptTheAppShips:
    """The two prompts cannot drift apart, because there is now only one.

    `evals/gec.py` used to define a near-copy of the shipped prompt: same job,
    three fields instead of four, its own worked examples. A score from it was
    a score for a prompt nobody was served, and the copies had already drifted
    on the one thing the eval measures -- the mitigation for a model flagging
    four of eight already-correct sentences reached the copy and not the
    original.

    The guard that held the shared half in both is gone with it. A test that
    asserts a thing equals itself is a test that can never fail, which is worse
    than no test: it reads like coverage.
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


