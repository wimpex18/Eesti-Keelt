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

import urllib.error

import pytest

from eesti.config import PROVIDER_TIMEOUT
from eesti.providers import breaker
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
