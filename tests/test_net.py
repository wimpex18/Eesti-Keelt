"""The retrying GET that two modules used to own a copy of each.

`rection.fetch` and `harvest/evkk.fetch` carried the same loop character for
character, and neither had a test: the harvesters' fetch halves are excluded
from the suite by a deliberate rule — a suite that re-crawls somebody's server
on every run is a suite that hammers it.

That rule is about the *network*, not about the logic wrapped around it. With
`urlopen` replaced, none of this touches a network, and what is left is exactly
the part that had two copies and could drift: how many attempts, how long it
waits between them, and what it says when it gives up.
"""

from __future__ import annotations

import urllib.request

import pytest

from eesti import net


@pytest.fixture
def no_sleeping(monkeypatch):
    """Record the back-off instead of serving it."""
    slept: list[float] = []
    monkeypatch.setattr(net.time, "sleep", slept.append)
    return slept


class _Response:
    def __init__(self, body: bytes):
        self._body = body

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _serving(*outcomes):
    """A fake `urlopen` playing the given outcomes in order.

    An outcome is either bytes to return or an exception to raise.
    """
    calls = []

    def urlopen(req, timeout=None):
        calls.append((req, timeout))
        outcome = outcomes[len(calls) - 1]
        if isinstance(outcome, Exception):
            raise outcome
        return _Response(outcome)

    urlopen.calls = calls
    return urlopen


class TestItFetches:
    def test_the_body_comes_back_as_text(self, monkeypatch, no_sleeping):
        monkeypatch.setattr(urllib.request, "urlopen", _serving(b"<html>ok</html>"))
        assert net.get("https://example.test/doc", "the document") == "<html>ok</html>"

    def test_broken_encoding_does_not_raise(self, monkeypatch, no_sleeping):
        """`errors="replace"`: a mis-encoded byte in a 200 KB handbook must not
        lose the whole fetch."""
        monkeypatch.setattr(urllib.request, "urlopen", _serving(b"kaks \xff kolm"))
        assert net.get("https://example.test/doc", "the document") == "kaks � kolm"

    def test_it_says_who_is_asking(self, monkeypatch, no_sleeping):
        """A tool that fetches somebody's server should be identifiable in
        their logs."""
        serve = _serving(b"ok")
        monkeypatch.setattr(urllib.request, "urlopen", serve)
        net.get("https://example.test/doc", "the document")
        req, _ = serve.calls[0]
        assert "Eesti-Keelt" in req.get_header("User-agent")

    def test_the_timeout_is_passed_through(self, monkeypatch, no_sleeping):
        serve = _serving(b"ok")
        monkeypatch.setattr(urllib.request, "urlopen", serve)
        net.get("https://example.test/doc", "the document", timeout=12.5)
        assert serve.calls[0][1] == 12.5


class TestItRetries:
    def test_a_transient_failure_is_retried(self, monkeypatch, no_sleeping):
        serve = _serving(OSError("connection reset"), b"second time lucky")
        monkeypatch.setattr(urllib.request, "urlopen", serve)
        assert net.get("https://example.test/doc", "doc") == "second time lucky"
        assert len(serve.calls) == 2

    def test_the_wait_grows(self, monkeypatch, no_sleeping):
        serve = _serving(OSError("one"), OSError("two"), b"third")
        monkeypatch.setattr(urllib.request, "urlopen", serve)
        net.get("https://example.test/doc", "doc")
        assert no_sleeping == [1, 2]

    def test_it_gives_up_after_the_attempts_it_promises(self, monkeypatch, no_sleeping):
        serve = _serving(*[OSError("down")] * 3)
        monkeypatch.setattr(urllib.request, "urlopen", serve)
        with pytest.raises(RuntimeError):
            net.get("https://example.test/doc", "doc")
        assert len(serve.calls) == net.RETRIES == 3

    def test_it_does_not_wait_after_the_last_attempt(self, monkeypatch, no_sleeping):
        """The sleep before giving up delays the exception and changes nothing.
        Both copies of this loop slept a final time; this one does not."""
        monkeypatch.setattr(urllib.request, "urlopen", _serving(*[OSError("x")] * 3))
        with pytest.raises(RuntimeError):
            net.get("https://example.test/doc", "doc")
        assert no_sleeping == [1, 2]


class TestTheFailureIsReadable:
    def test_it_names_the_document_and_the_last_error(self, monkeypatch, no_sleeping):
        """"unreachable" without a subject is not an error report, and the
        caller of a failed harvest is the person who reads this."""
        monkeypatch.setattr(urllib.request, "urlopen",
                            _serving(*[OSError("no route to host")] * 3))
        with pytest.raises(RuntimeError) as caught:
            net.get("https://example.test/doc", "EVKK taxonomy")
        assert "EVKK taxonomy" in str(caught.value)
        assert "no route to host" in str(caught.value)


class TestBothCallersStillUseIt:
    """The point of the module. If a caller grows its own loop again, the
    behaviour it shares stops being shared and nothing says so."""

    @pytest.mark.parametrize("module", ["eesti.rection", "eesti.harvest.evkk"])
    def test_the_fetcher_goes_through_net(self, module):
        import importlib
        import inspect

        source = inspect.getsource(importlib.import_module(module).fetch)
        assert "net.get(" in source, f"{module}.fetch no longer uses net.get"
        assert "urlopen" not in source, f"{module}.fetch opens its own connection"
