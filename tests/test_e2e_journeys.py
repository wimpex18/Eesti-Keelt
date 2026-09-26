"""The journeys a learner actually walks, driven in a real browser.

Contract tests check names; these check that a person can open a panel, answer
an item and see a verdict, at desktop and phone sizes, in Chromium and WebKit.

Skipped (never failed) without Playwright, a browser or a built dataset. CI's
`journeys` job builds the word list and runs them. The server runs in a temp working directory, so the learner databases
(relative `data/*.db` paths) are isolated, and the content databases point at
the real read-only ones via `EESTI_DB` / `EESTI_CONTENT_DB`.

Tests target roles, labels and visible outcomes rather than CSS classes.
"""

from __future__ import annotations

import os
import json
import re
import shutil
import sqlite3
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

from eesti.env import KNOWN_KEYS

pytest.importorskip("playwright", reason="browser suite: pip install playwright")

from playwright.sync_api import sync_playwright  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

from conftest import browsers_root, chromium_binary  # noqa: E402


#: Where Chromium is. Discovered per platform in `conftest.browsers_root` --
#: the container's path alone made every journey skip on a Mac.
def _chromium() -> str | None:
    return chromium_binary(browsers_root())


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def chromium_path() -> str:
    path = _chromium()
    if not path:
        pytest.skip("no Chromium binary — run `playwright install chromium`")
    return path


def _has_texts(path: Path) -> bool:
    """The corpus has rows (opening it creates an empty file, so existence is not
    enough).
    """
    if not path.exists():
        return False
    try:
        with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as conn:
            return conn.execute(
                "SELECT 1 FROM items WHERE body != '' LIMIT 1").fetchone() is not None
    except sqlite3.Error:
        return False


def _has_forms(path: Path) -> bool:
    """The form index `cli export` writes has rows; every word card reads it."""
    if not path.exists():
        return False
    try:
        with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as conn:
            return conn.execute("SELECT 1 FROM forms LIMIT 1").fetchone() is not None
    except sqlite3.Error:
        return False


@pytest.fixture(scope="session")
def corpus() -> None:
    """Skip a journey that needs reading texts when none are built."""
    if os.environ.get("EESTI_E2E_NO_CORPUS") or not _has_texts(ROOT / "data" / "content.db"):
        pytest.skip("no reading corpus — run `python -m eesti.cli harvest-reading`")


@pytest.fixture(scope="session")
def live_server(tmp_path_factory) -> str:
    """A real uvicorn process, isolated from the learner's study record.

    Learner databases are relative paths resolved at call time, so running the
    server from a scratch directory isolates them; content databases are passed
    through read-only.
    """
    from eesti.wordlist import available

    words, content = ROOT / "data" / "eesti.db", ROOT / "data" / "content.db"
    # Rows for the word list, not existence: an empty one would run every journey
    # against no lexicon.
    from eesti.lookup import EDGE_DB

    if not available(words) or not _has_forms(EDGE_DB):
        pytest.skip("no built dataset — run `python -m eesti.cli build` and "
                    "`python -m eesti.cli export`")

    workdir = tmp_path_factory.mktemp("e2e-server")
    (workdir / "data").mkdir()
    # The reading journey needs *some* corpus; copy rather than share so a test
    # that records exposure cannot write into the real content database. With no
    # corpus (CI) the app starts on an empty one and the journeys that read a
    # text skip through `corpus`.
    if _has_texts(content) and not os.environ.get("EESTI_E2E_NO_CORPUS"):
        shutil.copy(content, workdir / "data" / "content.db")

    port = _free_port()
    env = {
        **os.environ,
        "EESTI_DB": str(words),
        "EESTI_CONTENT_DB": str(workdir / "data" / "content.db"),
        "EESTI_ASR_EVAL_DIR": str(workdir / "data" / "eval" / "asr"),
        "PYTHONPATH": str(ROOT),
        # Keep the run offline and deterministic: every key the app knows
        # (`env.KNOWN_KEYS`) is blanked, since the server loads `.env` itself, so the
        # grammar chain degrades to Vabamorf.
        **{name: "" for name in KNOWN_KEYS},
    }
    # The app writes one JSON line per API call to stdout (`eesti/logs.py`). A
    # pipe nobody reads fills after a few hundred of them and the server blocks
    # in `write()` for the rest of the run, so every later page load times out
    # and the suite reports a defect the app does not have. A file always drains.
    log = workdir / "server.log"
    handle = log.open("w")
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "eesti.app:app",
         "--host", "127.0.0.1", "--port", str(port), "--log-level", "warning"],
        cwd=workdir, env=env,
        stdout=handle, stderr=subprocess.STDOUT, text=True,
    )
    base = f"http://127.0.0.1:{port}"
    try:
        import urllib.request
        for _ in range(120):
            if proc.poll() is not None:
                pytest.skip(f"server exited: {log.read_text()[-400:]}")
            try:
                urllib.request.urlopen(base + "/api/health", timeout=1).read()
                break
            except Exception:
                time.sleep(0.25)
        else:
            pytest.skip("server never became ready")
        yield base
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
        handle.close()


def _engines() -> list[str]:
    """Which engines this machine can drive: Chromium always, WebKit (Safari's engine)
    when installed.
    """
    root = browsers_root()
    engines = ["chromium"]
    if root.is_dir() and any(root.glob("webkit-*")):
        engines.append("webkit")
    return engines


#: One browser per test class, not per session: a long-lived WebKit browser stops
#: loading pages after many tests while the Mac's display is off.
@pytest.fixture(scope="class", params=_engines())
def _pw(request, chromium_path):
    with sync_playwright() as p:
        if request.param == "webkit":
            browser = p.webkit.launch()
        else:
            browser = p.chromium.launch(executable_path=chromium_path)
        browser.engine_name = request.param
        yield browser
        browser.close()


#: The two viewports: phone (the main use) and desktop.
VIEWPORTS = {
    "desktop": {"viewport": {"width": 1440, "height": 900}},
    "phone": {"viewport": {"width": 393, "height": 852},
              "is_mobile": True, "has_touch": True},
}


@pytest.fixture
def service_workers():
    return "allow"


@pytest.fixture(params=list(VIEWPORTS), ids=list(VIEWPORTS))
def page(request, _pw, live_server, service_workers):
    """A page at one viewport, with console errors, page errors and 5xx responses
    collected for assertions.
    """
    context = _pw.new_context(service_workers=service_workers, **VIEWPORTS[request.param])
    pg = context.new_page()
    pg.errors, pg.failed_requests = [], []
    pg.on("pageerror", lambda e: pg.errors.append(str(e)[:300]))
    pg.on("console",
          lambda m: m.type == "error" and pg.errors.append(f"console: {m.text[:200]}"))
    pg.on("response",
          lambda r: r.status >= 500 and pg.failed_requests.append(f"{r.status} {r.url}"))
    pg.goto(live_server, wait_until="networkidle")
    pg.viewport_name = request.param
    pg.engine_name = getattr(_pw, "engine_name", "chromium")
    yield pg
    context.close()


#: mode -> tabs its navigation offers; derived from the page in
#: `test_every_advertised_tab_is_reachable`.
MODES = ("learn", "revise", "exam")


def mode_of(page, tab: str) -> str:
    """Which mode's navigation offers this tab, asked of the page."""
    owner = page.evaluate(
        """(t) => {
             const b = document.querySelector(
               `nav[data-mode-nav] button[data-tab="${t}"]`);
             return b ? b.closest("nav").dataset.modeNav : null;
           }""", tab)
    assert owner, f"no navigation offers a {tab!r} tab"
    return owner


def open_tab(page, mode: str, tab: str) -> None:
    """Switch mode only when it is not already showing, as a learner would (one tap,
    no extra history entry).
    """
    if page.get_attribute(f'button[data-mode="{mode}"]', "aria-selected") != "true":
        page.click(f'button[data-mode="{mode}"]')
        page.wait_for_timeout(200)
    page.click(f'nav[data-mode-nav="{mode}"] button[data-tab="{tab}"]')
    page.wait_for_timeout(400)


def advertised_tabs(page, mode: str) -> list[str]:
    return page.eval_on_selector_all(
        f'nav[data-mode-nav="{mode}"] button[data-tab]', "els=>els.map(e=>e.dataset.tab)")


class TestNavigation:
    """Every panel opens, and only one at a time."""

    def test_every_advertised_tab_is_reachable(self, page):
        """Both directions, as `test_ui_contract` learned to do: every button
        the navigation offers must open a panel that actually appears."""
        unreachable = []
        for mode in MODES:
            for tab in advertised_tabs(page, mode):
                open_tab(page, mode, tab)
                if not page.is_visible(f"#tab-{tab}"):
                    unreachable.append(f"{mode}/{tab}")
        assert not unreachable, f"advertised but never shown: {unreachable}"

    def test_exactly_one_panel_is_visible_at_a_time(self, page):
        """Exactly one panel visible at every tab."""
        for mode in MODES:
            for tab in advertised_tabs(page, mode):
                open_tab(page, mode, tab)
                shown = page.eval_on_selector_all(
                    "section.panel", "els=>els.filter(e=>!e.hasAttribute('hidden')).map(e=>e.id)")
                assert shown == [f"tab-{tab}"], f"{mode}/{tab}: visible panels {shown}"

    def test_only_one_navigation_bar_is_laid_out(self, page):
        """Only one navigation bar is laid out, measured as geometry."""
        for mode in MODES:
            page.click(f'button[data-mode="{mode}"]')
            page.wait_for_timeout(250)
            laid_out = page.eval_on_selector_all(
                "nav[data-mode-nav]",
                "els=>els.filter(e=>getComputedStyle(e).display!=='none').map(e=>e.dataset.modeNav)")
            assert laid_out == [mode], f"mode {mode}: navigation bars laid out {laid_out}"

    def test_switching_tabs_throws_nothing(self, page):
        for mode in MODES:
            for tab in advertised_tabs(page, mode):
                open_tab(page, mode, tab)
        assert not page.errors, page.errors
        assert not page.failed_requests, page.failed_requests


#: The rendered counterpart of `test_ui_language.TestEachLabelIsReadInItsLanguage`,
#: over what the modules actually wrote: a Russian gloss resolves to `ru`; Latin
#: text inside a control, form label, option, link, heading or tag resolves to
#: `et` unless it is a code (`A1–B1`, `EKK 7.2`); Cyrillic text never resolves
#: to `et`. Text mixing both scripts (an option that cannot hold markup) is
#: skipped.
_WRONG_VOICE = r"""() => {
  const LATIN = /[A-Za-zÀ-ÿŠŽšžÕÄÖÜõäöü]/, CYR = /[Ѐ-ӿ]/;
  const NEUTRAL = /^(?:[A-Z0-9][A-Z0-9.+×–-]*|\d[\d.,×%\/–-]*|[a-z0-9-]+(?:\.[a-z0-9-]+)+)$/;
  const LABEL = "button,summary,label,option,legend,a,h1,h2,h3,h4,h5,h6,[role=tab],.tag";
  const langOf = el => el.closest("[lang]")?.getAttribute("lang") || "";
  const bad = [];
  for (const g of document.querySelectorAll(".ru"))
    if (langOf(g) !== "ru") bad.push(`gloss ${g.textContent.trim()}`);
  const walk = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  for (let n; (n = walk.nextNode());) {
    const el = n.parentElement, t = n.data.trim();
    if (!el || !t || el.closest("script,style")) continue;
    const latin = LATIN.test(t), cyr = CYR.test(t);
    if (cyr && !latin && langOf(el) === "et") bad.push(`Russian read as et: ${t.slice(0, 40)}`);
    const words = t.split(/[\s·—→←↗✓✗■()«»:,;!?+]+/).filter(Boolean);
    if (latin && !cyr && !words.every(w => NEUTRAL.test(w))
        && el.closest(LABEL) && !el.closest(".ru") && langOf(el) !== "et")
      bad.push(`Estonian read as ru: <${el.tagName.toLowerCase()}> ${t.slice(0, 40)}`);
  }
  return bad;
}"""


class TestEachLabelIsReadInItsLanguage:
    """A screen reader picks its voice from `lang`; the page is `ru`."""

    def test_every_tab_marks_its_estonian_and_its_russian(self, page):
        wrong = set()
        for mode in MODES:
            for tab in advertised_tabs(page, mode):
                open_tab(page, mode, tab)
                wrong |= {f"{mode}/{tab}: {w}" for w in page.evaluate(_WRONG_VOICE)}
        assert not wrong, (f"{page.viewport_name}: text in the wrong voice:\n  "
                           + "\n  ".join(sorted(wrong)))

    def test_a_label_changed_at_run_time_changes_its_voice(self, page):
        """`setLabel` swaps `Kontrolli` for `Проверяю…` while the check runs."""
        open_tab(page, "learn", "write")
        page.fill("#text", "Ma lugesin raamatut.")
        page.click("#checkBtn")
        page.wait_for_function(
            "() => !document.querySelector('#checkBtn').disabled", timeout=30000)
        assert page.get_attribute("#checkBtn", "lang") == "et"
        assert page.get_attribute("#checkBtn .ru", "lang") == "ru"


class TestTheGrammarDrill:
    """The offline core: generated items graded without a model or the network."""

    def _start(self, page):
        """Rada's Vaba harjutus: the same drills, recorded nowhere, so these checks
        leave the learner's path as they found it."""
        open_tab(page, mode_of(page, "path"), "path")
        page.click('#pathModes button[data-pm="vaba"]')
        page.wait_for_selector("#freeTopic option", state="attached", timeout=15000)
        page.click("#freeBtn")
        page.wait_for_selector("#freeOut .drill", timeout=15000)

    def test_starting_a_drill_renders_items(self, page):
        self._start(page)
        assert page.locator("#freeOut .drill").count() >= 1

    def test_a_wrong_answer_is_marked_wrong_and_explained(self, page):
        """A verdict without the reason teaches the answer, not the rule --
        and the reason is in Russian by the project's language rule, while the
        term stays Estonian."""
        self._start(page)
        item = page.locator("#freeOut .drill").first
        item.locator("input").fill("kindlasti-vale-vorm")
        item.locator("input").press("Enter")
        verdict = item.locator(".verdict")
        verdict.wait_for(state="visible", timeout=5000)
        assert "✗" in verdict.inner_text()
        assert "no" in (verdict.get_attribute("class") or "")
        assert len(verdict.inner_text()) > 20, "marked wrong with no explanation"

    def test_an_answered_item_cannot_be_answered_twice(self, page):
        """A second click cannot submit another answer for a graded item."""
        self._start(page)
        item = page.locator("#freeOut .drill").first
        item.locator("input").fill("vale")
        item.locator("input").press("Enter")
        page.wait_for_timeout(400)
        first = item.locator(".verdict").inner_text()
        assert item.locator("input").is_disabled(), "graded item still accepts input"
        # The check button is spent with the item, so a second submission has no way in.
        assert item.get_by_role("button", name="Kontrolli", exact=False, include_hidden=True).is_disabled(), "graded item's check button is live"
        mic = item.locator(".mic")
        if mic.count():
            assert mic.is_disabled(), "graded item's microphone is live"
        item.locator("input").press("Enter")
        page.wait_for_timeout(400)
        assert item.locator(".verdict").inner_text() == first

    def test_an_empty_answer_does_not_consume_the_item(self, page):
        """The first item is focused on load, but a stray Enter does not submit it."""
        self._start(page)
        item = page.locator("#freeOut .drill").first
        item.locator("input").press("Enter")
        page.wait_for_timeout(500)
        assert not item.locator("input").is_disabled(), "empty answer locked the item"
        assert item.locator(".verdict").inner_text().strip(), "no nudge shown"
        assert "✗" not in item.locator(".verdict").inner_text()
        assert page.locator("#freeScore").inner_text().strip() == "", "empty answer was scored"

    def test_a_question_word_blank_carries_a_russian_cue(self, page):
        """`küsisõnad` has no lemma to gloss; its blank carries EVS's Russian
        for the wanted word, marked Russian, and never the Estonian answer."""
        with sqlite3.connect(ROOT / "data" / "eesti.db") as conn:
            try:
                cued = conn.execute("SELECT COUNT(*) FROM evs_question").fetchone()[0]
            except sqlite3.Error:
                cued = 0
        if not cued:
            pytest.skip("no `evs_question` rows — run `cli import-evs`")
        open_tab(page, mode_of(page, "path"), "path")
        page.click('#pathModes button[data-pm="vaba"]')
        page.wait_for_selector("#freeTopic option", state="attached", timeout=15000)
        page.select_option("#freeTopic", "kusisonad")
        page.click("#freeBtn")
        page.wait_for_selector("#freeOut .drill", timeout=15000)
        # Visibility is asked of the gloss only where its drill is on screen:
        # the set shows one item at a time, which may be a cue-less one.
        glosses = page.eval_on_selector_all(
            "#freeOut .drill .task .gloss",
            """els=>els.map(e=>[e.lang, e.textContent,
                 !e.closest('.drill').checkVisibility() || e.checkVisibility()])""")
        assert glosses, "no question-word item showed a cue"
        from eesti.patterns import QUESTIONS

        answers = {w for q in QUESTIONS for w in q.word.casefold().split()}
        for lang, text, visible in glosses:
            assert lang == "ru"
            assert re.fullmatch(r"[а-яё ,]+", text), text
            assert not answers & set(re.findall(r"\w+", text.casefold()))
            assert visible, "a shown item's cue is hidden"
        assert not page.errors, page.errors

    def test_the_score_counts_only_answered_items(self, page):
        self._start(page)
        item = page.locator("#freeOut .drill").first
        item.locator("input").fill("vale")
        item.locator("input").press("Enter")
        page.wait_for_timeout(400)
        assert "/1" in page.locator("#freeScore").inner_text()


class TestTheWordWorkout:
    """Sõnatrenn: Russian meaning in, Estonian word out, graded against the word
    list. The scratch server has no learning words, so the set is topped up with
    the commonest new ones -- a slow status lookup once left the learner on
    "Подбираю слова…" for good."""

    def _start(self, page):
        open_tab(page, mode_of(page, "sonad"), "sonad")
        page.click("#workoutStart")
        page.wait_for_selector("#workoutOut .word-q", timeout=5000)

    def test_a_workout_starts_promptly_with_ten_words(self, page):
        self._start(page)
        assert page.locator("#workoutOut .word-q").count() == 10
        assert page.locator("#workoutOut .word-meaning").first.inner_text().strip()

    def test_a_wrong_word_shows_the_list_spelling_and_offers_review(self, page):
        self._start(page)
        item = page.locator("#workoutOut .word-q").first
        item.locator("input").fill("kindlasti-vale")
        item.locator("input").press("Enter")
        verdict = item.locator(".verdict")
        verdict.wait_for(state="visible", timeout=5000)
        assert "no" in (verdict.get_attribute("class") or "")
        assert verdict.locator("ins").inner_text().strip(), "the right word is not shown"
        assert verdict.locator("button[data-queue]").is_visible()
        assert page.locator("#workoutScore").inner_text().startswith("0/1")

    def test_an_empty_answer_does_not_consume_the_word(self, page):
        self._start(page)
        item = page.locator("#workoutOut .word-q").first
        item.locator("input").press("Enter")
        page.wait_for_timeout(300)
        assert not item.locator("input").is_disabled()
        assert page.locator("#workoutScore").inner_text().strip() == ""


@pytest.mark.usefixtures("corpus")
class TestReading:
    """List, open, read, come back. The journey that had 82 unopenable items."""

    def _load(self, page):
        open_tab(page, "learn", "read")
        page.click("#loadLib")
        page.wait_for_selector("#libList .lib-item", timeout=20000)

    def test_the_list_loads_and_says_how_many(self, page):
        self._load(page)
        assert page.locator("#libList .lib-item").count() > 0
        assert page.locator("#libCount").inner_text().strip()

    def test_opening_a_text_shows_its_body_and_hides_the_list(self, page):
        self._load(page)
        page.locator("#libList .lib-item").first.click()
        page.wait_for_selector("#reader:not([hidden])", timeout=15000)
        assert page.locator("#readerTitle").inner_text().strip()
        assert len(page.locator("#readerBody").inner_text()) > 30
        assert not page.is_visible("#libList")

    def test_going_back_returns_to_the_list(self, page):
        self._load(page)
        page.locator("#libList .lib-item").first.click()
        page.wait_for_selector("#reader:not([hidden])", timeout=15000)
        page.click("#backToLib")
        page.wait_for_timeout(400)
        assert page.is_visible("#libList")
        assert not page.is_visible("#reader")

    def test_translate_refuses_politely_with_nothing_selected(self, page):
        """The crutch is offered, never automatic. With no selection it must
        say what to do rather than translate the whole text or throw."""
        self._load(page)
        page.locator("#libList .lib-item").first.click()
        page.wait_for_selector("#reader:not([hidden])", timeout=15000)
        page.click("#xlBtn")
        page.wait_for_timeout(600)
        assert not page.is_visible("#xlOut")
        assert page.locator("#xlHint").inner_text().strip()
        assert not page.errors, page.errors

    def test_clicking_a_word_opens_a_card(self, page):
        """`<w>` elements are the lookup surface; a text whose words are not
        clickable is a reader with no dictionary."""
        self._load(page)
        page.locator("#libList .lib-item").first.click()
        page.wait_for_selector("#readerBody w", timeout=15000)
        page.locator("#readerBody w").first.click()
        page.wait_for_selector("#wordCard:not([hidden])", timeout=10000)
        # The card unhides with a skeleton and fills when `/api/lookup` answers: wait for
        # the answer, then check it is an analysis rather than a refusal.
        page.wait_for_function(
            "document.querySelector('#wordCard').innerText.trim().length > 0",
            timeout=10000)
        text = page.locator("#wordCard").inner_text().strip()
        assert "разбор недоступен" not in text, text


class TestWriting:
    """The writing check must answer with no provider key at all -- offline
    degradation is a feature here, not a failure."""

    def test_an_empty_submission_says_what_is_missing(self, page):
        """An empty submission shows a Russian message instead of doing nothing."""
        open_tab(page, "learn", "write")
        page.click("#checkBtn")
        page.wait_for_timeout(800)
        said = page.locator("#checkOut").inner_text().strip()
        assert said, "empty submit still gives no feedback"
        assert any("Ѐ" <= ch <= "ӿ" for ch in said), f"not in Russian: {said!r}"
        assert not page.locator("#checkBtn").is_disabled(), "empty submit locked the button"

    def test_a_real_sentence_gets_an_answer_without_any_key(self, page):
        open_tab(page, "learn", "write")
        page.fill("#text", "Ma lugesin raamatut läbi.")
        page.click("#checkBtn")
        page.wait_for_function(
            "()=>!document.querySelector('#checkBtn').disabled", timeout=90000)
        assert len(page.locator("#checkOut").inner_text().strip()) > 0
        assert not page.errors, page.errors

    def test_the_button_is_restored_after_a_check(self, page):
        """A button left saying "Kontrollin…" is a dead screen."""
        open_tab(page, "learn", "write")
        page.fill("#text", "Ma sõin suppi.")
        page.click("#checkBtn")
        page.wait_for_function(
            "()=>!document.querySelector('#checkBtn').disabled", timeout=90000)
        assert "Kontrolli" in page.locator("#checkBtn").inner_text()


class TestTheExamOverview:
    def test_switching_level_changes_what_is_shown(self, page):
        open_tab(page, "exam", "exam")
        page.wait_for_timeout(600)
        a2 = page.locator("#tab-exam").inner_text()
        page.click('#tab-exam button[data-level="B1"]')
        page.wait_for_timeout(1200)
        assert page.get_attribute('#tab-exam button[data-level="B1"]', "aria-selected") == "true"
        assert page.locator("#tab-exam").inner_text() != a2

    def test_the_verdict_never_reads_as_a_prediction(self, page):
        """A caveat nobody can read is not a caveat: the readiness screen must
        carry its Russian warning, because in Estonian it did the opposite of
        its job."""
        open_tab(page, "exam", "exam")
        page.wait_for_timeout(800)
        text = page.locator("#tab-exam").inner_text()
        assert any("Ѐ" <= ch <= "ӿ" for ch in text), \
            "no Cyrillic on the readiness screen — the caveat is unreadable to its reader"


class TestTheTabsKeyboardPattern:
    """The tab list is a real ARIA tab list: `aria-controls`, `role="tabpanel"`, arrow
    keys.
    """

    def test_every_tab_points_at_the_panel_it_opens(self, page):
        wiring = page.evaluate("""()=>{
          const tabs=[...document.querySelectorAll('[role="tab"][data-tab]')];
          return tabs.map(t=>({tab:t.dataset.tab,
            controls:t.getAttribute('aria-controls'),
            panelRole:document.getElementById('tab-'+t.dataset.tab)?.getAttribute('role'),
            labelled:document.getElementById('tab-'+t.dataset.tab)?.getAttribute('aria-labelledby')}));}""")
        assert wiring, "no tabs found"
        for w in wiring:
            assert w["controls"] == f"tab-{w['tab']}", w
            assert w["panelRole"] == "tabpanel", w
            assert w["labelled"], w

    def test_arrow_keys_move_between_tabs(self, page):
        """The neighbour tab is read off the page: ArrowRight moves one tab and its panel."""
        order = page.evaluate(
            """()=>[...document.querySelectorAll(
                 'nav[data-mode-nav="learn"] button[data-tab]')]
                 .map(b=>b.dataset.tab)""")
        first, second = order[0], order[1]

        page.click(f'nav[data-mode-nav="learn"] button[data-tab="{first}"]')
        page.wait_for_timeout(300)
        page.keyboard.press("ArrowRight")
        page.wait_for_timeout(400)
        assert page.evaluate("()=>document.activeElement.dataset.tab") == second
        assert page.is_visible(f"#tab-{second}"), "focus moved but the panel did not"
        page.keyboard.press("ArrowLeft")
        page.wait_for_timeout(400)
        assert page.evaluate("()=>document.activeElement.dataset.tab") == first

    def test_home_and_end_reach_the_ends(self, page):
        order = page.evaluate(
            """()=>[...document.querySelectorAll(
                 'nav[data-mode-nav="learn"] button[data-tab]')]
                 .map(b=>b.dataset.tab)""")
        page.click(f'nav[data-mode-nav="learn"] button[data-tab="{order[1]}"]')
        page.wait_for_timeout(300)
        page.keyboard.press("End")
        page.wait_for_timeout(400)
        assert page.evaluate("()=>document.activeElement.dataset.tab") == order[-1]
        page.keyboard.press("Home")
        page.wait_for_timeout(400)
        assert page.evaluate("()=>document.activeElement.dataset.tab") == order[0]

    def test_only_the_selected_tab_is_in_the_tab_order(self, page):
        """Roving tabindex: Tab should step past the strip, not through ten
        buttons inside it."""
        page.click('nav[data-mode-nav="learn"] button[data-tab="read"]')
        page.wait_for_timeout(300)
        order = page.eval_on_selector_all(
            'nav[data-mode-nav="learn"] button[data-tab]',
            "els=>els.map(e=>[e.dataset.tab, e.tabIndex])")
        assert [t for t, i in order if i == 0] == ["read"], order


class TestTheSelectedSkillIsVisible:
    """The selected tab is scrolled into view in the phone's horizontally scrolling
    navigation, whatever tab the page opened on.
    """

    @pytest.mark.parametrize("tab", ["write", "speak", "sonad"])
    def test_a_deep_link_scrolls_the_row_to_it(self, page, live_server, tab):
        page.goto(f"{live_server}#{tab}", wait_until="networkidle")
        page.wait_for_timeout(400)
        verdict = page.evaluate("""()=>{
          const nav=document.querySelector('nav[data-mode-nav]:not([hidden])');
          const sel=nav.querySelector('button[aria-selected="true"]');
          if(!sel) return 'no selected tab';
          const r=sel.getBoundingClientRect(), n=nav.getBoundingClientRect();
          return (r.left>=n.left-1 && r.right<=n.right+1) ? null
               : `${sel.dataset.tab} is ${Math.round(r.right-n.right)}px outside the row`;}""")
        assert verdict is None, f"{page.viewport_name}: {verdict}"

    def test_the_page_itself_is_not_scrolled_to_do_it(self, page, live_server):
        """Without scrolling the document itself (`scrollIntoView` would)."""
        page.goto(f"{live_server}#write", wait_until="networkidle")
        page.wait_for_timeout(400)
        assert page.evaluate("()=>Math.round(window.scrollY)") == 0


class TestTheMiddleWidth:
    """720-1079px: the rail layout. Marks must have real size and buttons an
    accessible name when labels are hidden.
    """

    @pytest.fixture
    def tablet(self, _pw, live_server):
        context = _pw.new_context(viewport={"width": 834, "height": 1000})
        pg = context.new_page()
        pg.goto(live_server, wait_until="networkidle")
        pg.wait_for_timeout(300)
        yield pg
        context.close()

    def test_the_rail_shows_its_labels(self, tablet):
        """A learner still learning the Estonian names cannot navigate by icon alone."""
        fits = tablet.eval_on_selector_all(
            "nav[data-mode-nav]:not([hidden]) .lbl",
            "els=>els.map(e=>e.checkVisibility() && e.scrollWidth <= e.clientWidth + 1)")
        assert fits and all(fits), fits

    def test_the_skills_are_a_column(self, tablet):
        assert tablet.eval_on_selector(
            "nav[data-mode-nav]:not([hidden])",
            "e=>getComputedStyle(e).flexDirection") == "column"

    def test_every_mark_is_drawn(self, tablet):
        bad = tablet.eval_on_selector_all(
            "nav[data-mode-nav]:not([hidden]) button",
            """els=>els.filter(b=>{const s=b.querySelector('.ico svg');
                 if(!s) return true; const r=s.getBoundingClientRect();
                 return !r.width || !r.height;}).map(b=>b.dataset.tab)""")
        assert not bad, f"marks with no size in the rail: {bad}"

    def test_every_button_still_has_a_name(self, tablet):
        """The label is `display:none` here, and `display:none` takes the text
        out of the accessibility tree with it."""
        unnamed = tablet.eval_on_selector_all(
            "nav[data-mode-nav]:not([hidden]) button",
            """els=>els.filter(b=>!(b.getAttribute('aria-label')||'').trim())
                 .map(b=>b.dataset.tab)""")
        assert not unnamed, f"rail buttons with no accessible name: {unnamed}"

    def test_the_rail_never_traps_its_own_last_entry(self, tablet):
        """A sticky column taller than the window pins at `top` and its bottom
        is never reachable by scrolling the page."""
        verdict = tablet.evaluate("""()=>{
          const n=document.querySelector('nav[data-mode-nav]:not([hidden])');
          const r=n.getBoundingClientRect();
          const last=n.querySelector('button:last-of-type').getBoundingClientRect();
          if (last.bottom > r.bottom + 1 && getComputedStyle(n).overflowY === 'visible')
            return 'the last skill is outside a rail that cannot scroll';
          return null;}""")
        assert verdict is None, verdict

    def test_the_page_does_not_scroll_sideways(self, tablet):
        over = tablet.evaluate(
            "()=>document.documentElement.scrollWidth-document.documentElement.clientWidth")
        assert over <= 1, f"{over}px of sideways scroll at 834px"


class TestMobileLayout:
    """Phone failure modes, asserted at both sizes."""

    def test_the_page_never_scrolls_sideways(self, page):
        for mode in MODES:
            for tab in advertised_tabs(page, mode):
                open_tab(page, mode, tab)
                over = page.evaluate(
                    "()=>document.documentElement.scrollWidth-window.innerWidth")
                assert over <= 1, f"{page.viewport_name} {mode}/{tab}: {over}px of sideways scroll"

    def test_the_last_control_is_not_trapped_under_the_navigation(self, page):
        """Scrolled to the bottom, each panel's last control is what the browser hits at
        its centre — not the fixed bar.
        """
        trapped = []
        for mode in MODES:
            for tab in advertised_tabs(page, mode):
                open_tab(page, mode, tab)
                # Scroll until the page stops growing: content that lands after
                # the scroll (Kuulamine's library sections, loaded one by one)
                # moves the last control, and the check is about the settled page.
                page.evaluate("""async () => {
                  let last = -1;
                  for (let i = 0; i < 40; i++) {
                    window.scrollTo(0, document.body.scrollHeight);
                    await new Promise(r => setTimeout(r, 250));
                    if (document.body.scrollHeight === last) return;
                    last = document.body.scrollHeight;
                  }
                }""")
                # `checkVisibility()` rather than a non-zero box: descendants of a collapsed
                # <details> have a rect while unrendered.
                verdict = page.evaluate("""()=>{
                  const p=document.querySelector('section.panel:not([hidden])');
                  const els=[...p.querySelectorAll('button,input,select,a')]
                    .filter(e=>{const r=e.getBoundingClientRect();
                                return r.height>0 && e.checkVisibility()
                                       && r.top<window.innerHeight && r.bottom>0;});
                  if(!els.length) return null;
                  const last=els[els.length-1], r=last.getBoundingClientRect();
                  const hit=document.elementFromPoint(r.left+r.width/2, r.top+r.height/2);
                  return (hit===last||last.contains(hit)||hit===null) ? null
                       : (last.innerText||last.tagName).trim().slice(0,20);}""")
                if verdict:
                    trapped.append(f"{mode}/{tab}:{verdict}")
        assert not trapped, f"{page.viewport_name}: controls covered by the nav: {trapped}"

    def test_tap_targets_are_big_enough_to_hit(self, page):
        """Only enforced on the phone; a mouse can hit a 20px target and a
        thumb cannot."""
        if page.viewport_name != "phone":
            pytest.skip("tap-target floor applies to touch viewports")
        small = page.eval_on_selector_all(
            "nav[data-mode-nav]:not([hidden]) button",
            """els=>els.filter(e=>{const r=e.getBoundingClientRect();
                 return r.height>0 && (r.height<32||r.width<32);})
               .map(e=>e.dataset.tab+':'+Math.round(e.getBoundingClientRect().height))""")
        assert not small, f"navigation targets under 32px: {small}"

    def test_touch_targets_meet_the_44px_floor(self, page):
        """Skill chips and the round header buttons, on a touch screen."""
        if page.viewport_name != "phone":
            pytest.skip("the 44px floor applies to touch viewports")
        small = page.eval_on_selector_all(
            "nav[data-mode-nav]:not([hidden]) button, .hdr-actions .iconbtn",
            """els=>els.filter(e=>{const r=e.getBoundingClientRect();
                 return r.height>0 && r.height<44;})
               .map(e=>(e.dataset.tab||e.id)+':'+Math.round(e.getBoundingClientRect().height))""")
        assert not small, f"touch targets under 44px: {small}"

    def test_a_phone_drill_shows_one_item_at_a_time(self, page):
        """Answered items and the next one are shown; the rest wait."""
        if page.viewport_name != "phone":
            pytest.skip("one item at a time is the phone layout")
        TestTheGrammarDrill()._start(page)
        visible = lambda: page.eval_on_selector_all(
            "#freeOut .drill", "els=>els.filter(e=>e.checkVisibility()).length")
        assert visible() == 1
        first = page.locator("#freeOut .drill").first
        first.locator("input").fill("vale")
        first.locator("input").press("Enter")
        page.wait_for_timeout(500)
        assert visible() == 2


class TestDiscoveredDefects:
    @pytest.fixture
    def service_workers(self):
        # WebKit's worker forwards requests outside Playwright's route hooks.
        # Stubbed regressions need page requests; offline journeys keep the worker.
        return "block"

    def test_long_word_card_keeps_close_and_actions_reachable(self, page):
        """A long EKI entry must scroll inside its card above the phone dock."""
        page.route("**/api/enrich/*", lambda r: r.fulfill(json={
            "found": True, "definition": "Näide", "examples": ["See on raamat."] * 40,
        }))
        open_tab(page, "revise", "sonad")
        word = page.locator("#vocOut button[data-word]").first
        word.wait_for(state="visible")
        word.click()
        page.wait_for_selector("#vocCard .examples li")
        page.locator("#vocCard #skipBtn").focus()
        assert page.locator("#vocCard #skipBtn").evaluate("""el => {
            const r = el.getBoundingClientRect();
            return el.contains(document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2));
        }""")
        close = page.locator("#vocCard .card-close")
        assert close.evaluate("""el => {
            const r = el.getBoundingClientRect();
            return r.width >= 44 && r.height >= 44 &&
              el.contains(document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2));
        }""")
        close.click()
        assert page.locator("#vocCard").is_hidden()
        assert not page.errors, page.errors

    def test_exam_video_opens_in_the_app(self, page, live_server):
        page.route("https://www.youtube-nocookie.com/embed/*", lambda r: r.fulfill(
            content_type="text/html", body="<html><body>Video</body></html>"))
        open_tab(page, "exam", "exam")
        video = page.locator("#examMaterial button[data-video]").first
        video.wait_for(state="visible")
        with page.expect_request("https://www.youtube-nocookie.com/embed/*") as embed:
            video.click()
        # YouTube rejects unidentified embeds with error 153. Send only the
        # app's origin, never its reading route or sentence.
        assert embed.value.all_headers().get("referer") == live_server + "/"
        iframe = page.locator("#examMaterial .exam-task iframe")
        iframe.wait_for(state="attached")
        assert iframe.get_attribute("src").startswith("https://www.youtube-nocookie.com/embed/")
        page.locator("#examMaterial .exam-task button").click()
        assert iframe.count() == 0
        assert not page.errors, page.errors

    def test_word_card_can_close_before_lookup_returns(self, page):
        """A slow dictionary must not trap the learner or reopen a dismissed card."""
        pending = []
        page.route("**/api/lookup/*", lambda route: pending.append(route))
        open_tab(page, "revise", "sonad")
        word = page.locator("#vocOut button[data-word]").first
        word.wait_for(state="visible")
        word.click()
        close = page.get_by_role("button", name="Sulge — закрыть", exact=True)
        close.wait_for(state="visible")
        assert pending
        close.press("Escape")
        assert page.locator("#vocCard").is_hidden()
        assert word.evaluate("el => el === document.activeElement")
        pending[0].fulfill(json={"found": False, "word": "test"})
        page.wait_for_load_state("networkidle")
        assert page.locator("#vocCard").is_hidden()
        assert not page.errors, page.errors

    def test_downloaded_workbook_opens_here_and_undownloaded_links_out(self, page):
        page.route("**/api/library?skill=eksam*", lambda r: r.fulfill(json={"items": [
            {"id": "qa-vihik", "title": "Konsultatsioonivihik", "external": False,
             "local": True, "format": "pdf", "file": True},
            {"id": "qa-external", "title": "Muu vihik", "external": True,
             "local": False, "format": "pdf", "url": "https://harno.ee/vihik.pdf"},
        ]}))
        page.route("**/api/exam/text/qa-vihik", lambda r: r.fulfill(json={"available": False}))
        page.route("**/api/exam/native/qa-vihik", lambda r: r.fulfill(json={"available": False}))
        page.route("**/api/exam/pages/qa-vihik", lambda r: r.fulfill(json={"pages": 1}))
        page.route("**/api/exam/page/qa-vihik/*", lambda r: r.fulfill(
            content_type="image/svg+xml", body='<svg xmlns="http://www.w3.org/2000/svg" width="100" height="120"><rect width="100" height="120" fill="white"/></svg>'))
        open_tab(page, "revise", "vihikud")
        page.get_by_role("button", name="Konsultatsioonivihik", exact=True).click()
        page.locator("#vihikudList .exam-pages img").wait_for(state="visible")
        assert page.get_by_role("link", name="Muu vihik", exact=True).get_attribute("href") == "https://harno.ee/vihik.pdf"
        page.locator("#vihikudList .exam-task [data-close]").click()
        assert page.locator("#vihikudList .exam-task").count() == 0
        assert not page.errors, page.errors

    def test_model_success_is_not_presented_as_deterministic_form_analysis(self, page):
        page.route("**/api/check", lambda r: r.fulfill(json={
            "corrections": [], "engine": "llm:workers-ai", "degraded": False}))
        open_tab(page, "learn", "write")
        page.fill("#text", "Ma elan Tallinnas.")
        page.click("#checkBtn")
        page.wait_for_selector("#checkOut .engine")
        text = page.locator("#checkOut").inner_text()
        assert "Модель не предложила исправлений" in text
        assert "не подтверждение правильности" in text
        assert "Разбор форм" not in text

    """Routing and preference behaviours a learner relies on."""

    def test_a_reload_keeps_you_where_you_were(self, page):
        """The open tab is in the hash, so a refresh returns to it."""
        open_tab(page, "exam", "status")
        assert page.is_visible("#tab-status")
        page.reload(wait_until="networkidle")
        page.wait_for_timeout(800)
        assert page.is_visible("#tab-status"), "reload lost the learner's place"

    def test_a_pasted_link_opens_that_tab(self, page, live_server):
        """Deep linking, which the page had no way to express before."""
        page.goto(live_server + "/#sonad", wait_until="networkidle")
        page.wait_for_timeout(800)
        assert page.is_visible("#tab-sonad")
        # Which nav owns the tab is asked of the page.
        owner = mode_of(page, "sonad")
        assert page.get_attribute(
            f'nav[data-mode-nav="{owner}"] button[data-tab="sonad"]',
            "aria-selected") == "true", "the tab opened but its button is not selected"

    def test_the_retired_drill_link_opens_free_practice(self, page, live_server):
        """`#drill` was Harjutused; a bookmark to it lands on the same drills."""
        page.goto(live_server + "/#drill", wait_until="networkidle")
        page.wait_for_timeout(800)
        assert page.is_visible("#tab-path")
        assert page.is_visible("#pathFree") and not page.is_visible("#pathRada")
        assert page.get_attribute('#pathModes button[data-pm="vaba"]',
                                  "aria-selected") == "true"

    def test_back_returns_to_the_previous_tab_not_out_of_the_app(self, page):
        """Back returns to the previous tab instead of leaving the app (a system gesture
        on phones).
        """
        open_tab(page, "learn", "read")
        open_tab(page, "learn", "write")
        assert page.is_visible("#tab-write")
        page.go_back()
        page.wait_for_timeout(600)
        assert page.is_visible("#tab-read"), "Back did not return to the previous tab"
        page.go_forward()
        page.wait_for_timeout(600)
        assert page.is_visible("#tab-write")

    def test_deep_linking_to_any_tab_raises_nothing(self, page, live_server):
        """Deep-linking to any tab raises nothing.

        Opening a tab runs its loader, which may touch late declarations; failures
        arrive as unhandled rejections, so visit each tab by URL and demand silence.
        """
        page.add_init_script(
            "window.addEventListener('unhandledrejection',"
            " e => console.error('UNHANDLED: ' + e.reason))")
        for mode in MODES:
            for tab in advertised_tabs(page, mode):
                page.errors.clear()
                page.goto(f"{live_server}/#{tab}", wait_until="networkidle")
                page.wait_for_timeout(700)
                assert page.is_visible(f"#tab-{tab}"), f"#{tab} did not open"
                assert not page.errors, f"#{tab} on {page.engine_name}: {page.errors}"

    def test_an_unknown_hash_falls_back_rather_than_showing_nothing(self, page, live_server):
        page.goto(live_server + "/#not-a-tab", wait_until="networkidle")
        page.wait_for_timeout(600)
        shown = page.eval_on_selector_all(
            "section.panel", "els=>els.filter(e=>!e.hasAttribute('hidden')).map(e=>e.id)")
        assert shown == ["tab-path"], shown

    def test_the_chosen_exam_level_survives_a_reload(self, page):
        """The chosen exam level survives a reload (localStorage: a view preference, not
        learner data).
        """
        open_tab(page, "exam", "exam")
        page.click('#tab-exam button[data-level="B1"]')
        page.wait_for_timeout(800)
        page.reload(wait_until="networkidle")
        open_tab(page, "exam", "exam")
        page.wait_for_timeout(800)
        assert page.get_attribute(
            '#tab-exam button[data-level="B1"]', "aria-selected") == "true"
        assert page.get_attribute(
            '#tab-exam button[data-level="A2"]', "aria-selected") == "false", \
            "both levels highlighted at once"

    @pytest.mark.usefixtures("corpus")
    def test_choosing_all_shows_more_than_one_difficulty(self, page):
        """Unfiltered browsing shows more than one difficulty band."""
        open_tab(page, "learn", "read")
        page.select_option("#readLevel", "")
        page.click("#loadLib")
        page.wait_for_selector("#libList .lib-item", timeout=20000)
        bands = page.eval_on_selector_all(
            "#libList .lib-item .lib-meta",
            "els=>[...new Set(els.map(e=>e.textContent.split('·')[0].trim()))]")
        assert len(bands) > 1, f"'kõik' returned only {bands}"

class TestEveryMarkIsActuallyDrawn:
    """Every navigation mark has a real rendered size, on phone and desktop."""

    def test_every_tab_mark_has_a_real_size(self, page):
        sizes = page.evaluate("""() =>
            [...document.querySelectorAll('nav[data-mode-nav] button[data-tab]')]
              .map(b => {
                const nav = b.closest('nav');
                if (nav.hidden) return null;
                const s = b.querySelector('.ico svg');
                if (!s) return {tab: b.dataset.tab, w: null, h: null};
                const r = s.getBoundingClientRect();
                return {tab: b.dataset.tab, w: Math.round(r.width),
                        h: Math.round(r.height)};
              }).filter(Boolean)""")
        assert sizes, "no visible tabs found -- the check would be vacuous"
        bad = [s for s in sizes if not s["w"] or not s["h"]]
        assert not bad, (
            f"marks with no size at {page.viewport_name}: {bad}")

    def test_the_marks_are_not_absurdly_large(self, page):
        """The other end of the same mistake: an unsized `<svg>` falls back to
        300x150, which would push the bar off the screen."""
        big = page.evaluate("""() =>
            [...document.querySelectorAll('.ico svg, .part-mark svg, .st svg')]
              .map(s => { const r = s.getBoundingClientRect();
                          return Math.round(Math.max(r.width, r.height)); })
              .filter(v => v > 40)""")
        assert not big, f"oversized marks at {page.viewport_name}: {big}"

class TestTheMeaningCardIsAFlashcard:
    """The vocabulary meaning card: the ratings are not reachable until the answer is
    shown (layout, so it needs a browser).
    """

    #: One word per engine and viewport: the live server and its `review.db` are shared,
    #: and grading a card leaves it not due for the next run. Each word is a glossed
    #: noun whose genitive and partitive coincide, so it is mined as a meaning card.
    WORD = {
        ("chromium", "desktop"): ("maja", "дом"),
        ("chromium", "phone"): ("tool", "стул"),
        ("webkit", "desktop"): ("arst", "врач"),
        ("webkit", "phone"): ("ema", "мать"),
    }

    def _word(self, page):
        return self.WORD[(page.engine_name, page.viewport_name)]

    def _queue_a_meaning_card(self, page, live_server):
        word, _ = self._word(page)
        return page.evaluate("""async ([base, word]) => {
            const r = await fetch(base + "/api/mine", {
              method: "POST", headers: {"Content-Type": "application/json"},
              body: JSON.stringify({word, context: "See on " + word + "."}),
            });
            return await r.json();
        }""", [live_server, word])

    def test_reveal_then_rate(self, page, live_server):
        """Reveal then grade, as one flow: a graded card is no longer due for a later test."""
        word, meaning = self._word(page)
        queued = self._queue_a_meaning_card(page, live_server)
        assert queued["queued"] and queued["kind"] == "vocab", queued

        page.click('.modes button[data-mode="revise"]')
        page.click("#loadReview")
        page.wait_for_selector(".flashcard", timeout=15000)

        card = page.locator(".flashcard").first
        assert card.locator(".fc-word").inner_text().strip() == word
        # The answer, and every rating, must be out of reach before the reveal.
        assert card.locator(".fc-back").is_hidden()
        assert card.locator("button[data-r]").first.is_hidden()

        card.locator(".fc-show").click()
        page.wait_for_timeout(300)
        assert card.locator(".fc-back").is_visible()
        assert meaning in card.locator(".fc-meaning").inner_text()
        assert card.locator("button[data-r]").first.is_visible()

        card.locator('button[data-r="good"]').click()
        page.wait_for_selector(".flashcard .verdict.ok", timeout=15000)
        verdict = card.locator(".verdict").inner_text()
        assert meaning in verdict and "снова" in verdict, verdict
        assert not page.errors, page.errors


class TestChoosingTheSitting:
    """Eksam shows the exam's own shape and lets the learner pick a sitting."""

    def test_the_spec_is_shown_and_a_sitting_can_be_chosen(self, page):
        open_tab(page, "exam", "exam")
        page.wait_for_selector("#examSpec .hint", timeout=15000)
        assert "48 из 80" in page.locator("#examSpec").inner_text()

        page.select_option("#goalSitting", "2026-11-07")
        page.click("#goalSet")
        page.wait_for_selector('#examGoal a[href="/api/goal.ics"]', timeout=15000)
        assert "до регистрации" in page.locator("#countdown").inner_text()
        assert not page.errors, page.errors


class TestTheConversationPartner:
    """Vestlus renders and says what it is, even with no engine configured —
    which is the state the journeys run in."""

    def test_it_starts_and_reports_honestly(self, page):
        open_tab(page, "learn", "speak")
        page.wait_for_selector("#vestlusStart", state="attached", timeout=15000)
        page.click("#vestlus > summary")
        assert "не проверяет и не оценивает" in page.locator("#vestlus").inner_text()
        page.click("#vestlusStart")
        page.wait_for_selector("#vestlusLog .hint", timeout=20000)
        assert "собеседник" in page.locator("#vestlusLog").inner_text().lower()
        assert not page.errors, page.errors

    def test_a_spoken_turn_is_reviewed_before_sending(self, _pw, live_server):
        context = _pw.new_context(service_workers="block", viewport={"width": 390, "height": 844})
        context.add_init_script("""(() => {
          Object.defineProperty(navigator, 'mediaDevices', {configurable: true,
            value: {getUserMedia: async () => ({getTracks: () => [{stop() {}}]})}});
          window.MediaRecorder = class {
            constructor() { this.mimeType = 'audio/wav'; this.state = 'inactive'; }
            start() { this.state = 'recording'; }
            stop() {
              this.state = 'inactive';
              this.ondataavailable({data: new Blob(['RIFFxxxx'], {type: 'audio/wav'})});
              this.onstop();
            }
          };
        })()""")
        try:
            page = context.new_page()
            errors = []
            sent = []
            page.on("pageerror", lambda e: errors.append(str(e)[:300]))
            page.route("**/api/asr", lambda route: route.fulfill(
                status=200, content_type="application/json",
                body=json.dumps({"ready": True, "hosted": True, "cloudflare": True})))

            def tutor(route):
                sent.append(route.request.post_data_json["said"])
                route.fulfill(status=200, content_type="application/json", body=json.dumps({
                    "reply_et": "Kus sa õpid?", "turns": len(sent), "engine": "test",
                    "hint_ru": "", "unknown": [], "note": ""}))

            page.route("**/api/tutor", tutor)
            page.route("**/api/speak", lambda route: route.fulfill(
                status=200, content_type="audio/wav", body=b"RIFFxxxx"))
            page.route("**/api/transcribe?*", lambda route: route.fulfill(
                status=200, content_type="application/json",
                body=json.dumps({"text": "Ma elan Tallinnas.", "engine": "test"})))
            page.goto(live_server, wait_until="networkidle")
            open_tab(page, "learn", "speak")
            page.click("#vestlus > summary")
            page.click("#vestlusStart")
            page.wait_for_selector("#vestlusRow:visible")
            page.click("#vestlusMic")
            page.click("#vestlusMic")
            page.wait_for_function("document.querySelector('#vestlusSay').value === 'Ma elan Tallinnas.'")
            assert sent == [""]  # the transcript has not gone to the tutor
            page.click("#vestlusSend")
            page.wait_for_selector("#vestlusLog .vestlus-me")
            assert sent == ["", "Ma elan Tallinnas."]
            # The partner's voice plays through the app's own player, which stands in
            # for the native element's controls (`js/media.js`).
            assert page.locator("#vestlusVoice + .player").is_visible()
            assert not errors, errors
        finally:
            context.close()


class TestSpeakingEvaluation:
    """The learner can collect question answers without treating ASR as truth."""

    @pytest.mark.usefixtures("corpus")
    def test_question_mode_offers_a_recordable_task(self, page):
        open_tab(page, "learn", "speak")
        page.click("#evalSet > summary")
        page.select_option("#evalMode", "answer")
        page.wait_for_function("document.querySelector('#evalRec').disabled === false")
        question = page.locator("#evalPrompt").inner_text()
        assert question.endswith(("?", "."))
        assert "чернов" in page.locator("#evalSet").inner_text()
        page.select_option("#evalMode", "read")
        page.wait_for_function("document.querySelector('#evalRec').disabled === false")
        assert page.locator("#evalPrompt").inner_text()
        assert not page.errors, page.errors

    def test_normal_answer_can_be_saved_and_reviewed_in_the_page(
            self, _pw, live_server):
        context = _pw.new_context(viewport={"width": 390, "height": 844})
        context.add_init_script("""(() => {
          Object.defineProperty(navigator, 'mediaDevices', {configurable: true,
            value: {getUserMedia: async () => ({getTracks: () => [{stop() {}}]})}});
          window.MediaRecorder = class {
            constructor() { this.mimeType = 'audio/wav'; this.state = 'inactive'; }
            start() { this.state = 'recording'; }
            stop() {
              this.state = 'inactive';
              this.ondataavailable({data: new Blob(['RIFFxxxx'], {type: 'audio/wav'})});
              this.onstop();
            }
          };
        })()""")
        try:
            page = context.new_page()
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)[:300]))
            page.goto(live_server, wait_until="networkidle")
            open_tab(page, "learn", "speak")
            page.select_option("#speakMode", "vastus")
            page.wait_for_selector("#speakPrompt")
            page.click("#recBtn")
            page.click("#recBtn")
            page.wait_for_selector("#recSaveEval:visible")
            page.click("#recSaveEval")
            page.wait_for_selector("#evalReview:visible")
            assert page.locator("#evalTranscript").input_value() == ""
            page.fill("#evalTranscript", "Ma elan Tallinnas.")
            page.check("#evalListened")
            page.click("#evalVerify")
            page.wait_for_function("document.querySelector('#evalReviewNote').textContent.includes('готова')")
            assert not errors, errors
        finally:
            context.close()

    @pytest.mark.parametrize("asr_state,expected", [
        ({"ready": True, "hosted": True, "cloudflare": True}, "Cloudflare"),
        ({"ready": True, "hosted": False, "local": True}, "на этом компьютере"),
    ])
    @pytest.mark.parametrize("viewport_name", list(VIEWPORTS))
    def test_audio_destination_matches_the_configured_engine(
            self, _pw, live_server, viewport_name, asr_state, expected):
        # Route the very first ASR request. A page fixture has already loaded
        # the app and may have a controlling service worker by the time a
        # route is installed, so it cannot test this initial disclosure.
        context = _pw.new_context(service_workers="block", **VIEWPORTS[viewport_name])
        try:
            page = context.new_page()
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)[:300]))
            page.route("**/api/asr", lambda route: route.fulfill(
                status=200, content_type="application/json",
                body=json.dumps(asr_state)))
            page.goto(live_server, wait_until="networkidle")
            open_tab(page, "learn", "speak")
            page.wait_for_function("expected => [document.querySelector('#recPrivacy'), "
                                   "document.querySelector('#evalPrivacy')]"
                                   ".every(el => el.textContent.includes(expected))",
                                   arg=expected)
            assert expected in page.locator("#recPrivacy").inner_text()
            assert expected in page.locator("#evalPrivacy").text_content()
            assert not errors, errors
        finally:
            context.close()


class TestTheWholeSitting:
    """Terve eksam: the parts come one after another, each with its own clock."""

    @pytest.mark.usefixtures("corpus")
    def test_the_run_moves_from_one_part_to_the_next(self, page):
        open_tab(page, "exam", "exam")
        page.wait_for_selector("#mockWhole", state="attached", timeout=15000)
        page.click("#mock > summary")
        page.click("#mockWhole")
        # Writing comes first in the exam's order.
        page.wait_for_selector("#mockWritten", timeout=20000)
        page.fill("#mockWritten", " ".join(["sõna"] * 35))
        page.click("#mockDone")
        page.wait_for_selector("#mockNext button", timeout=20000)
        assert "слов" in page.locator("#mockVerdict").inner_text()

        page.click("#mockNext button")           # kuulamine
        page.wait_for_selector("#mockTasks .mock-task", timeout=20000)
        assert not page.errors, page.errors


class TestTestingOutOfATopic:
    """Kogu rada offers a test-out; five right marks the topic known."""

    def test_a_clean_sweep_marks_the_topic(self, page, live_server):
        open_tab(page, "learn", "path")
        # The list lives inside a closed <details>: attached first, then opened.
        page.wait_for_selector("#pathList .topic", state="attached", timeout=20000)
        page.click("#pathAll > summary")
        button = page.locator("#pathList button[data-testout]").first
        button.wait_for(timeout=10000)
        topic = button.get_attribute("data-testout")
        button.click()
        page.wait_for_selector("#testoutTasks input", timeout=20000)

        # The answers come from the API, as a learner who knows them would type.
        answers = page.evaluate("""async ([base, topic]) => {
            const r = await fetch(`${base}/api/testout/${topic}`);
            return await r.json();
        }""", [live_server, topic])
        inputs = page.locator("#testoutTasks input")
        assert inputs.count() == len(answers["items"])
        page.click("#testoutDone")
        page.wait_for_selector("#testoutVerdict.ok, #testoutVerdict.no", timeout=20000)
        assert "из" in page.locator("#testoutVerdict").inner_text()
        assert not page.errors, page.errors


class TestTheTimedMock:
    """Proovieksam: one part, on the exam's clock, graded by the server."""

    @pytest.mark.usefixtures("corpus")
    def test_a_reading_section_runs_and_is_recorded(self, page):
        open_tab(page, "exam", "exam")
        page.wait_for_selector("#mockParts button[data-part]", state="attached",
                               timeout=15000)
        page.click("#mock > summary")
        page.click('#mockParts button[data-part="lugemine"]')
        page.wait_for_selector("#mockTasks .mock-task input", timeout=20000)
        assert re.match(r"\d\d:\d\d", page.locator("#mockClock").inner_text())

        page.locator("#mockTasks .mock-task input").first.fill("vale")
        page.click("#mockDone")
        page.wait_for_selector("#mockVerdict.ok", timeout=20000)
        verdict = page.locator("#mockVerdict").inner_text()
        assert "из" in verdict and "не оценка экзамена" in verdict
        assert not page.errors, page.errors


class TestPractisingOffline:
    """A set fetched in advance is answerable with the network cut, and what was
    answered reaches the server when it comes back."""

    @pytest.mark.usefixtures("corpus")
    def test_download_go_offline_answer_come_back(self, page, live_server):
        open_tab(page, "learn", "path")
        page.wait_for_selector("#offlineGet", state="attached", timeout=15000)
        page.click("#offline > summary")
        page.click("#offlineGet")
        page.wait_for_selector("#offlinePractice:not([hidden])", timeout=20000)

        page.context.set_offline(True)
        try:
            page.click("#offlinePractice")
            page.wait_for_selector("#practiceOut .banner.info", timeout=15000)
            page.wait_for_selector("#practiceOut .drill input", timeout=15000)
            first = page.locator("#practiceOut .drill").first
            first.locator("input").fill("ilmselgelt vale")
            first.locator("button").click()
            page.wait_for_selector("#practiceOut .verdict.no", timeout=15000)
            # The verdict appears first; the queue write follows it.
            page.wait_for_function(
                "() => document.querySelector('#practiceOut .verdict')"
                ".textContent.includes('локально')", timeout=15000)
            page.wait_for_selector("#offlineSend:not([hidden])", timeout=15000)
        finally:
            page.context.set_offline(False)

        # Coming back online flushes the queue by itself, so the send button
        # goes away; clicking it is only for a flush that failed.
        page.wait_for_function(
            "() => document.querySelector('#offlineSend').hidden", timeout=20000)
        answered = page.evaluate("""async () => {
            const r = await fetch('/api/curriculum');
            const d = await r.json();
            return d.topics.reduce((n, t) => n + t.attempts, 0);
        }""")
        assert answered >= 1, "the offline answer never reached the server"
        assert not page.errors, page.errors


class TestTodaysPlan:
    """Rada opens on today's plan; a block's Alusta starts what it names."""

    def test_the_plan_is_there_and_starts_practice(self, page):
        open_tab(page, "learn", "path")
        page.wait_for_selector("#todayList .today-block", state="attached", timeout=15000)
        if not page.locator("#today").evaluate("d => d.open"):
            page.click("#today > summary")
        blocks = page.locator("#todayList .today-block")
        assert blocks.count() >= 1
        assert "мин" in blocks.first.locator(".today-min").inner_text()
        start = page.locator('#todayList .today-block[data-kind="new"] button')
        if start.count():
            start.first.click()
            page.wait_for_selector("#practiceOut .drill", timeout=15000)
        assert not page.errors, page.errors


class TestAGrammarCardIsAnswered:
    """A grammar card in the queue is answered, and code rates it; there are no
    self-rating buttons on it (`review.auto_rating`)."""

    def test_type_the_form_and_see_the_verdict(self, page, live_server):
        # A card of its own per engine and viewport: the server's queue is shared,
        # and an answered card is no longer due for the next run.
        lemma = f"e2e-{page.engine_name}-{page.viewport_name}"
        prompt = f"Kui mul oleks aega, ____ ma kinno ({lemma})."
        page.evaluate("""async ([base, lemma, prompt]) => {
            await fetch(base + "/api/review", {
              method: "POST", headers: {"Content-Type": "application/json"},
              body: JSON.stringify({kind: "tingiv", lemma, prompt, answer: "läheksin"}),
            });
        }""", [live_server, lemma, prompt])

        page.click('.modes button[data-mode="revise"]')
        card = self._reach(page, live_server, lemma)
        assert card.locator("button[data-r]").count() == 0
        card.locator("input").fill("läheksin")
        if page.viewport_name == "phone":
            # The phone keyboard's Enter: emulation has no keyboard, so a tap on
            # Kontrolli blurs the field and the mode bar, hidden while typing,
            # comes back under the pointer before the click lands.
            card.locator("input").press("Enter")
        else:
            card.locator("button[data-check]").click()
        page.wait_for_selector(f".drill.done:has-text('{lemma}') .verdict.ok", timeout=15000)
        verdict = card.locator(".verdict").inner_text()
        assert "Верно" in verdict and "снова" in verdict, verdict
        assert not page.errors, page.errors

    @staticmethod
    def _reach(page, base, lemma):
        """Open the queue with this test's card at its head.

        The queue shows one unanswered card at a time, and the server is shared:
        other journeys leave cards due (a wrong answer queues one), which would
        stand in front of this card. They are rated "easy" first, out of today.
        A card whose learning step falls due in between is cleared on another
        pass.
        """
        for _ in range(3):
            page.evaluate("""async ([base, lemma]) => {
                const due = (await (await fetch(base + "/api/review?limit=1000")).json()).items;
                for (const it of due.filter(it => it.lemma !== lemma))
                  await fetch(base + "/api/review/grade", {
                    method: "POST", headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({id: it.id, rating: "easy"}),
                  });
            }""", [base, lemma])
            page.click("#loadReview")
            head = page.locator("#reviewOut > .drill").first
            head.wait_for(timeout=15000)
            if lemma in head.inner_text():
                return head
        raise AssertionError(f"another card stayed ahead of {lemma}: {head.inner_text()}")


#: axe-core, the accessibility rule engine, as a dev dependency (`package.json`).
#: Skipped rather than failed when it is not installed: the journeys already
#: need Playwright and a built dataset, and one more optional tool should not
#: make the suite unrunnable.
AXE = ROOT / "node_modules" / "axe-core" / "axe.min.js"


class TestEveryScreenIsReadableByAScreenReader:
    """The interface is Estonian and its explanations are Russian, which only
    works if the markup says which is which — and a learner using VoiceOver on
    the installed PWA meets every screen, not a chosen one. WCAG 2.1 A and AA,
    checked by axe on each tab."""

    def test_no_screen_has_an_accessibility_violation(self, page, live_server):
        if not AXE.is_file():
            pytest.skip("axe-core is not installed: npm install")
        found = []
        for mode in MODES:
            for tab in advertised_tabs(page, mode):
                open_tab(page, mode, tab)
                page.add_script_tag(content=AXE.read_text(encoding="utf-8"))
                violations = page.evaluate("""async () => {
                  const run = await axe.run(document, {
                    resultTypes: ["violations"],
                    runOnly: {type: "tag",
                              values: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]},
                  });
                  return run.violations.map(v => ({
                    id: v.id, impact: v.impact, help: v.help,
                    where: v.nodes[0].target.join(" "), count: v.nodes.length,
                  }));
                }""")
                found += [f"{mode}/{tab}: {v['impact']} {v['id']} — {v['help']}"
                          f" ({v['count']}x, first at {v['where']})"
                          for v in violations]
        assert not found, (f"{page.viewport_name}: "
                           + "\n  ".join(["accessibility violations:"] + found))


class TestPhoneInLandscape:
    """iPhone 17 on its side: 874×402, touch. Wider than the phone breakpoint, so
    the layout has to recognise it by height and input, not width."""

    @pytest.fixture
    def landscape(self, _pw, live_server):
        context = _pw.new_context(viewport={"width": 874, "height": 402},
                                  has_touch=True)
        pg = context.new_page()
        pg.goto(live_server + "/#path", wait_until="networkidle")
        pg.wait_for_selector("#practiceOut .drill", timeout=20000)
        yield pg
        context.close()

    def test_one_drill_at_a_time(self, landscape):
        visible = landscape.eval_on_selector_all(
            "#practiceOut .drill", "els=>els.filter(e=>e.checkVisibility()).length")
        assert visible == 1

    def test_the_drill_starts_in_the_upper_part_of_the_screen(self, landscape):
        top = landscape.eval_on_selector(
            "#practiceOut .drill", "e=>e.getBoundingClientRect().top")
        assert top < 402 * 0.8, f"first drill starts at {top}px of 402"

    def test_nothing_scrolls_sideways(self, landscape):
        assert landscape.evaluate(
            "document.scrollingElement.scrollWidth <= innerWidth + 1")
