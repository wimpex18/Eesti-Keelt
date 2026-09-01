"""Every field an endpoint returns, checked against something that reads it.

`tests/test_route_inventory.py` asks whether each *route* has a caller. This
asks the same question one level finer: does each **field** have a reader? The
two failures are the same shape, and this project has now found both — an
endpoint nothing called (`/api/modes`), and fields nothing read.

Found on 2026-08-22 by enumerating live responses and grepping the page:

- `/api/exam/{level}` returned `muu`, the bucket `exam_material` fills with
  every kind no named group claimed, precisely so nothing is lost. The page
  rendered the five named groups and dropped the bucket, so a kind the
  harvesters had not been taught about would vanish from that screen without a
  trace. Only `konsultatsioon` lands there today and it has its own tab, which
  is exactly why nobody noticed.
- `/api/readiness/{level}` returned `grammar.outstanding` — the exact topics
  standing between this learner and this level, the most actionable thing the
  verdict computes — and `vocabulary`, and `deadline.note`, the sentence that
  explains an empty countdown. None reached the screen.
- `/api/review/stats` returned `struggling`: the words that keep coming back
  wrong. A count says the queue is working; the names say what to look at.
- `/api/reading/next` returned `unmeasurable`, counted by its own comment
  "rather than silently dropped" — and then dropped by the page, restoring the
  contradiction it was added to prevent.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from test_e2e_journeys import chromium_path, live_server  # noqa: F401

from pagesrc import markup_and_script

ROOT = Path(__file__).resolve().parents[1]

#: Endpoints whose whole payload is meant for the page, and the GET that
#: exercises each. Kept small and explicit: a list that tried to cover every
#: route would be a list of exemptions within a week.
ENDPOINTS = (
    "/api/curriculum",
    "/api/exam/B1",
    "/api/readiness/B1",
    "/api/review/stats",
    "/api/reading/next?limit=2",
    "/api/library?skill=lugemine&limit=2",
)

#: Fields that exist for somebody other than the page, with the reader named.
#: An exemption has to say who reads it, or it is just a silenced test.
NOT_FOR_THE_PAGE = {
    "boot": "the Worker, to notice a restarted container",
    "origin_guarded": "the smoke workflow's guard check",
    "built": "the smoke workflow, to date the image",
    "revision": "the smoke workflow, when the builder passes BUILD_REV",
    "rules": "the object-case generator's own inventory",
    "library": "the smoke workflow's harvest warning",
    "threshold": "documentation of how the ranking was computed",
    "limit": "the page's paging arithmetic, via libShown",
    "offset": "the page's paging arithmetic, via libShown",
    "outstanding_ids": "a caller that needs identity rather than a label",
    "by_kind": "the CLI's review summary",
    "days_to_decide": "the countdown string the verdict builds from it",
    "days_to_sitting": "the countdown string the verdict builds from it",
}


@pytest.fixture(scope="module")
def page() -> str:
    text = markup_and_script()
    assert len(text) > 50_000, "page unexpectedly small — nothing would be checked"
    return text


def reads(page: str, key: str) -> bool:
    """Does the page mention this field at all?

    Deliberately generous — property access, destructuring, a string key. The
    question being asked is "is this field wired to anything", and a false
    *pass* on a field that is mentioned but unused is a far cheaper mistake
    than a false failure on every destructured name.
    """
    return re.search(r'[.\["\'{,\s]' + re.escape(key) + r'\b', page) is not None


class TestEveryFieldHasAReader:
    def test_the_endpoints_answer(self, client):
        for url in ENDPOINTS:
            assert client.get(url).status_code == 200, url

    @pytest.mark.parametrize("url", ENDPOINTS)
    def test_no_field_is_computed_and_never_read(self, client, page, url):
        body = client.get(url).json()
        assert isinstance(body, dict) and body, url
        orphans = [k for k in body
                   if k not in NOT_FOR_THE_PAGE and not reads(page, k)]
        assert not orphans, f"{url} returns fields nothing reads: {orphans}"

    def test_every_exemption_names_its_reader(self):
        """An exemption with an empty reason is a silenced test."""
        for key, why in NOT_FOR_THE_PAGE.items():
            assert why and len(why) > 8, key

    def test_the_check_can_fail(self, client, page):
        """A generous matcher plus a long page is how this passes vacuously."""
        assert not reads(page, "zzz_field_that_cannot_exist")


class TestTheFieldsThisWasWrittenFor:
    """Driven in a browser, because the question is whether a value reaches
    the screen and no amount of grepping can answer that.

    The string version of these was written first and two of the five passed
    with the rendering disabled -- `if (false) { ... material.muu.map(...) }`
    still contains the words `material.muu`. A matcher generous enough to
    survive destructuring is far too generous to prove a value was displayed.
    That is the same vacuity this suite has now caught four times, and the
    browser is the only reader that cannot be fooled by it.
    """

    #: Payloads shaped like the real ones, each carrying a value that used to
    #: be computed and dropped. The marker strings are what must appear.
    STUBS = {
        "**/api/exam/**": ({
            "level": "B1", "sooritusnaidis": [], "video": [], "kirjeldus": [],
            "teave": [], "ulesanded": {},
            "muu": [{"id": "m1", "title": "ZZKONSULTATSIOON",
                     "skill": "kirjutamine", "url": "https://example.invalid/1",
                     "format": "pdf"}],
        }, "ZZKONSULTATSIOON"),
        "**/api/readiness/**": ({
            "level": "B1", "parts": [], "reasons": [], "caveat": "",
            "countdown": "",
            "grammar": {"topics": 9, "mastered": 2,
                        "outstanding": ["ZZSONAJARG"], "checkpoint_passed": False},
            "vocabulary": {"known": 7, "level_words": 2509, "measured": True},
            "deadline": {"registration": None, "sitting": None,
                         "note": "ZZNOCOUNTDOWN"},
        }, "ZZSONAJARG"),
        "**/api/review/stats": ({
            "total": 3, "due": 1, "by_kind": {"osastav": 1},
            "struggling": [{"lemma": "ZZREEGEL", "kind": "osastav",
                            "lapses": 4, "reps": 6}],
        }, "ZZREEGEL"),
    }

    @pytest.fixture(scope="class")
    def screen(self, live_server, chromium_path):
        """Every stubbed panel's rendered text, in one browser session.

        Run on a thread of its own. `TestClient` leaves an asyncio event loop
        installed in the thread it ran on, and Playwright's sync API refuses to
        start inside one -- so this passed alone and failed in the full suite,
        purely because of which modules had run first. A fresh thread has no
        loop, which makes the outcome independent of test order.
        """
        from concurrent.futures import ThreadPoolExecutor

        with ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(self._drive, live_server, chromium_path).result()

    @classmethod
    def _drive(cls, live_server: str, chromium_path: str) -> dict:
        import json as _json

        from playwright.sync_api import sync_playwright

        seen = {}
        with sync_playwright() as pw:
            browser = pw.chromium.launch(executable_path=chromium_path)
            page = browser.new_context(viewport={"width": 1280, "height": 1000}).new_page()
            errors: list[str] = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            # A factory, not `lambda route, b=body:`. Playwright inspects the
            # handler's arity and calls a two-parameter one as (route,
            # request) -- so the default argument was overwritten with a
            # Request object and every stub tried to serialise it.
            def stub(payload):
                def handler(route):
                    route.fulfill(status=200, content_type="application/json",
                                  body=_json.dumps(payload))
                return handler

            for pattern, (body, _) in cls.STUBS.items():
                page.route(pattern, stub(body))
            # `domcontentloaded`, not `networkidle`: the stubs fulfil some
            # requests and leave others to the real server, and waiting for the
            # whole page to fall quiet under that mix timed out every run.
            page.goto(live_server, wait_until="domcontentloaded")
            page.wait_for_selector('button[data-mode="exam"]', timeout=15000)

            # Waits on the panel, never on the elements under test: a fixture
            # that waits for the thing it is about to assert turns every real
            # failure into a fixture error, which reads as a broken test rather
            # than a broken page.
            page.click('button[data-mode="exam"]')
            page.wait_for_selector("#tab-exam:not([hidden])", timeout=15000)
            page.wait_for_timeout(900)
            seen["exam"] = page.locator("#tab-exam").inner_text()

            page.click('button[data-mode="revise"]')
            page.wait_for_selector("#tab-review:not([hidden])", timeout=15000)
            page.wait_for_timeout(700)
            seen["review"] = page.locator("#tab-review").inner_text()

            seen["errors"] = errors
            browser.close()
        return seen

    def test_the_page_did_not_throw(self, screen):
        assert not screen["errors"], screen["errors"]

    def test_the_exam_screen_renders_the_leftover_bucket(self, screen):
        assert "ZZKONSULTATSIOON" in screen["exam"]

    def test_the_verdict_names_the_topics_that_are_left(self, screen):
        assert "ZZSONAJARG" in screen["exam"]

    def test_the_verdict_reports_vocabulary(self, screen):
        assert "2509" in screen["exam"]

    def test_an_empty_countdown_explains_itself(self, screen):
        assert "ZZNOCOUNTDOWN" in screen["exam"]

    def test_the_queue_names_what_keeps_failing(self, screen):
        assert "ZZREEGEL" in screen["review"]

    def test_unmeasurable_texts_are_counted_on_screen(self, page):
        """The one left as source inspection: reaching it needs a corpus whose
        texts resolve no lemmas, which the fixture cannot produce."""
        assert "d.unmeasurable" in page


class TestTopicIdsNeverReachTheLearner:
    """The fourth occurrence. `uhildumine` and `sonajark` are database keys
    with the diacritics stripped; the topics are called `ühildumine` and
    `sõnajärg`, and the readiness screen printed the keys."""

    def test_outstanding_holds_names(self):
        from eesti.curriculum import TOPICS
        from eesti.readiness import _grammar

        import sqlite3
        conn = sqlite3.connect(":memory:")
        from eesti.progress import connect as progress_connect
        conn.close()
        conn = progress_connect(":memory:")

        got = _grammar(conn, "B1")
        ids = {t.id for t in TOPICS}
        names = {t.et for t in TOPICS}
        assert got["outstanding"], "no outstanding topics — nothing checked"
        assert set(got["outstanding"]) <= names
        assert not (set(got["outstanding"]) & (ids - names))
        assert set(got["outstanding_ids"]) <= ids

    def test_the_reason_string_a_learner_reads_holds_no_ids(self, client):
        body = client.get("/api/readiness/B1").json()
        from eesti.curriculum import TOPICS

        joined = " ".join(body["reasons"])
        assert joined, "no reasons — nothing checked"

        # Names first, then ids in what is left. `umbisikuline tegumood` is a
        # real topic name that *begins* with its own id, so searching the raw
        # string for bare ids flags a correct label -- which is what the first
        # version of this test did.
        rest = joined
        for topic in sorted(TOPICS, key=lambda t: -len(t.et)):
            rest = rest.replace(topic.et, " ")
        leaked = sorted({t.id for t in TOPICS if t.id != t.et
                         and re.search(rf"\b{re.escape(t.id)}\b", rest)})
        assert not leaked, f"database keys shown to the learner: {leaked}"
