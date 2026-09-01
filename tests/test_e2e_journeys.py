"""The journeys a learner actually walks, driven in a real browser.

Why this exists at all. `test_ui_contract.py` asks whether the page and the API
agree about *names*, and `test_web_layout.py` pins one CSS line because a
browser found a bug no markup test could see -- two fixed navigation bars
painting on top of each other, because `nav{display:flex}` out-specifies
`[hidden]{display:none}`. Both are proxies. Neither can answer "can a person
open this panel, answer this item, and see a verdict", which is the only
question that matters and the one that has repeatedly gone wrong here: 82
indexed-but-unopenable items, a reading list that returned zero texts for every
filter, `POST /api/vocab/known` with no caller on the deployment.

Why it skips instead of failing. This project's rule is that an optional
dependency or a third party must never fail the build, and the deliberate
choice on record is *not* to put a browser in CI. So every test here skips
unless Playwright, a Chromium binary and a live server are all present. On a
developer machine `pytest tests/test_e2e_journeys.py` runs them; in CI they
report as skipped, which is honest, rather than as passed, which would not be.

Conventions followed from the rest of the suite: no test touches the learner's
real databases -- the server subprocess runs in a temp working directory, so
the four relative learner paths (`data/progress.db` and friends) resolve inside
it, and the two content databases are pointed at the real read-only ones
through `EESTI_DB` / `EESTI_CONTENT_DB`.

Tests are written against roles, labels and user-visible outcomes rather than
CSS classes, so a restyle does not break them. Where a real defect was found
during the UAT pass it is marked `xfail(strict=True)`: the suite stays green,
the defect stays documented, and the day somebody fixes it the strict marker
turns the unexpected pass into a failure that says "delete this marker".
"""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

pytest.importorskip("playwright", reason="browser suite: pip install playwright")

from playwright.sync_api import sync_playwright  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

#: Where the container keeps Chromium. `PLAYWRIGHT_BROWSERS_PATH` is set for us,
#: but the folder name carries a build number, so it is discovered rather than
#: hardcoded -- a pinned number is a test that breaks on an unrelated upgrade.
def _chromium() -> str | None:
    root = Path(os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "/opt/pw-browsers"))
    if not root.is_dir():
        return None
    for path in sorted(root.glob("chromium-*/chrome-linux/chrome")):
        return str(path)
    for path in sorted(root.glob("chromium*/**/chrome")):
        return str(path)
    return None


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


@pytest.fixture(scope="session")
def live_server(tmp_path_factory) -> str:
    """A real uvicorn process, isolated from the learner's study record.

    The learner databases are *relative* paths resolved at call time
    (`data/progress.db`), which is what makes this isolation possible: run the
    server from a scratch directory and they land there. The content databases
    are absolute and read-only for our purposes, so they are passed through --
    building a 160 000-word wordlist per test run would make this unrunnable.
    """
    from eesti.wordlist import available

    words, content = ROOT / "data" / "eesti.db", ROOT / "data" / "content.db"
    # Rows for the word list, not existence. An empty one passes `exists()`,
    # and then the whole journey suite runs against a zero-word lexicon: every
    # drill empty, every lookup missing, ~140 failures that look like a
    # regression and are a missing build. That is the same gate `real_wordlist`
    # was fixed for, in the file where it would be loudest.
    if not available(words) or not content.exists():
        pytest.skip("no built dataset — run `python -m eesti.cli build`")

    workdir = tmp_path_factory.mktemp("e2e-server")
    (workdir / "data").mkdir()
    # The reading journey needs *some* corpus; copy rather than share so a test
    # that records exposure cannot write into the real content database.
    shutil.copy(content, workdir / "data" / "content.db")

    port = _free_port()
    env = {
        **os.environ,
        "EESTI_DB": str(words),
        "EESTI_CONTENT_DB": str(workdir / "data" / "content.db"),
        "PYTHONPATH": str(ROOT),
        # Keep the run offline and deterministic: no provider key means the
        # grammar chain degrades to Vabamorf, which is what we want to assert.
        "OPENROUTER_API_KEY": "", "GROQ_API_KEY": "",
        "ANTHROPIC_API_KEY": "", "CLOUDFLARE_API_TOKEN": "",
    }
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "eesti.app:app",
         "--host", "127.0.0.1", "--port", str(port), "--log-level", "warning"],
        cwd=workdir, env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    base = f"http://127.0.0.1:{port}"
    try:
        import urllib.request
        for _ in range(120):
            if proc.poll() is not None:
                pytest.skip(f"server exited: {(proc.stdout.read() or '')[-400:]}")
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


def _engines() -> list[str]:
    """Which engines this machine can actually drive.

    Chromium is always expected; WebKit is included only when installed, so
    the suite still runs on a machine that has not fetched it. WebKit is not
    decoration: it is Safari's engine, this app is used on a phone, and the
    first WebKit run found a real error both engines had -- Chromium reported
    it as an unhandled rejection nobody was listening for, WebKit raised it
    where it could be seen.
    """
    root = Path(os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "/opt/pw-browsers"))
    engines = ["chromium"]
    if root.is_dir() and any(root.glob("webkit-*")):
        engines.append("webkit")
    return engines


@pytest.fixture(scope="session", params=_engines())
def _pw(request, chromium_path):
    with sync_playwright() as p:
        if request.param == "webkit":
            browser = p.webkit.launch()
        else:
            browser = p.chromium.launch(executable_path=chromium_path)
        browser.engine_name = request.param
        yield browser
        browser.close()


#: The two shapes that matter. The phone is the one this app is mostly used on;
#: the desktop is the one where a whole column of layout went unlooked-at for
#: months. Both, every time, is the lesson already written down in CLAUDE.md.
VIEWPORTS = {
    "desktop": {"viewport": {"width": 1440, "height": 900}},
    "phone": {"viewport": {"width": 390, "height": 844},
              "is_mobile": True, "has_touch": True},
}


@pytest.fixture(params=list(VIEWPORTS), ids=list(VIEWPORTS))
def page(request, _pw, live_server):
    """A page at one viewport, with console and network errors collected.

    Errors are attached to the page object so any test can assert on them, and
    a few do: a journey that "works" while throwing a TypeError on every click
    is not working, it is failing quietly.
    """
    context = _pw.new_context(**VIEWPORTS[request.param])
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


#: mode -> the tabs its navigation offers. Derived from the page in
#: `test_every_advertised_tab_is_reachable`, not trusted from here: a
#: hand-maintained copy of a list that already exists is exactly how `TABS`
#: drifted from the panels and three of ten never showed.
MODES = ("learn", "revise", "exam")


def mode_of(page, tab: str) -> str:
    """Which mode's navigation offers this tab, asked of the page.

    `open_tab(page, "exam", "drill")` was hardcoded, and when free practice
    moved out of the exam mode and into Õppimine on 2026-08-21 it broke twelve
    journeys at once. The rest of this file already derives its tab lists for
    exactly that reason; this closes the last place that did not.
    """
    owner = page.evaluate(
        """(t) => {
             const b = document.querySelector(
               `nav[data-mode-nav] button[data-tab="${t}"]`);
             return b ? b.closest("nav").dataset.modeNav : null;
           }""", tab)
    assert owner, f"no navigation offers a {tab!r} tab"
    return owner


def open_tab(page, mode: str, tab: str) -> None:
    """Switch mode only when the mode is not already showing.

    A learner moving from Lugemine to Kirjutamine taps one button, not two.
    Clicking the mode every time made the helper walk a path no user walks,
    and once the open tab lived in the URL that difference showed up as a
    history entry nobody had chosen.
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
    """The seam that has broken most often: a panel that exists and cannot be
    opened, or two that open at once."""

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
        """Two panels painting at once is the documented `[hidden]` bug in its
        general form. Counted at every tab, because it only showed on one."""
        for mode in MODES:
            for tab in advertised_tabs(page, mode):
                open_tab(page, mode, tab)
                shown = page.eval_on_selector_all(
                    "section.panel", "els=>els.filter(e=>!e.hasAttribute('hidden')).map(e=>e.id)")
                assert shown == [f"tab-{tab}"], f"{mode}/{tab}: visible panels {shown}"

    def test_only_one_navigation_bar_is_laid_out(self, page):
        """The bug `test_web_layout` pins one CSS line for, asserted as the
        geometry a person would see rather than as a rule in a stylesheet."""
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


class TestTheGrammarDrill:
    """The offline core: generated items, graded without a model. If anything
    in this class needs the network, the app's central property has broken."""

    def _start(self, page):
        open_tab(page, mode_of(page, "drill"), "drill")
        page.click("#drillBtn")
        page.wait_for_selector("#drillOut .drill", timeout=15000)

    def test_starting_a_drill_renders_items(self, page):
        self._start(page)
        assert page.locator("#drillOut .drill").count() >= 1

    def test_a_wrong_answer_is_marked_wrong_and_explained(self, page):
        """A verdict without the reason teaches the answer, not the rule --
        and the reason is in Russian by the project's language rule, while the
        term stays Estonian."""
        self._start(page)
        item = page.locator("#drillOut .drill").first
        item.locator("input").fill("kindlasti-vale-vorm")
        item.locator("input").press("Enter")
        verdict = item.locator(".verdict")
        verdict.wait_for(state="visible", timeout=5000)
        assert "✗" in verdict.inner_text()
        assert "no" in (verdict.get_attribute("class") or "")
        assert len(verdict.inner_text()) > 20, "marked wrong with no explanation"

    def test_an_answered_item_cannot_be_answered_twice(self, page):
        """Found in a browser once already: a second click submitted another
        answer for a graded item and the accuracy gate counted it."""
        self._start(page)
        item = page.locator("#drillOut .drill").first
        item.locator("input").fill("vale")
        item.locator("input").press("Enter")
        page.wait_for_timeout(400)
        first = item.locator(".verdict").inner_text()
        assert item.locator("input").is_disabled(), "graded item still accepts input"
        item.locator("button").click()
        page.wait_for_timeout(400)
        assert item.locator(".verdict").inner_text() == first

    def test_an_empty_answer_does_not_consume_the_item(self, page):
        """QA-3, fixed. The first item is focused on load, so one stray Enter
        used to lock a question, score it wrong, and count that against the
        accuracy which gates mastery."""
        self._start(page)
        item = page.locator("#drillOut .drill").nth(2)
        item.locator("input").press("Enter")
        page.wait_for_timeout(500)
        assert not item.locator("input").is_disabled(), "empty answer locked the item"
        assert item.locator(".verdict").inner_text().strip(), "no nudge shown"
        assert "✗" not in item.locator(".verdict").inner_text()
        assert page.locator("#score").inner_text().strip() == "", "empty answer was scored"

    def test_the_score_counts_only_answered_items(self, page):
        self._start(page)
        item = page.locator("#drillOut .drill").first
        item.locator("input").fill("vale")
        item.locator("input").press("Enter")
        page.wait_for_timeout(400)
        assert "/1" in page.locator("#score").inner_text()


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
        assert page.locator("#wordCard").inner_text().strip()


class TestWriting:
    """The writing check must answer with no provider key at all -- offline
    degradation is a feature here, not a failure."""

    def test_an_empty_submission_says_what_is_missing(self, page):
        """QA-4, fixed. It used to return silently, which is indistinguishable
        from a dead button. The message is Russian because that is the language
        every explanation in this app is written in."""
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
    """QA-7, fixed. The page declared `role="tab"` on every navigation button
    and implemented none of the rest: no `aria-controls`, no `role="tabpanel"`,
    arrow keys inert. A screen reader announces a tab list, which tells its
    user to expect exactly those things."""

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
        """The *neighbour* is read off the page, not named here.

        This asserted `path -> read`, which stopped being true the moment a tab
        was inserted between them. What the test is about is that ArrowRight
        moves one tab and takes the panel with it; which tab that happens to be
        is a fact about the navigation, and the navigation is right there to
        ask."""
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


class TestMobileLayout:
    """Everything here is a phone-only failure mode. They run at both sizes on
    purpose: a rule that only holds on one is the bug, not the test."""

    def test_the_page_never_scrolls_sideways(self, page):
        for mode in MODES:
            for tab in advertised_tabs(page, mode):
                open_tab(page, mode, tab)
                over = page.evaluate(
                    "()=>document.documentElement.scrollWidth-window.innerWidth")
                assert over <= 1, f"{page.viewport_name} {mode}/{tab}: {over}px of sideways scroll"

    def test_the_last_control_is_not_trapped_under_the_navigation(self, page):
        """Scrolled to the bottom, the final control of each panel must be the
        thing the browser hits at its own centre -- not the fixed bar."""
        trapped = []
        for mode in MODES:
            for tab in advertised_tabs(page, mode):
                open_tab(page, mode, tab)
                page.evaluate("()=>window.scrollTo(0,document.body.scrollHeight)")
                page.wait_for_timeout(300)
                # `checkVisibility()` rather than a non-zero box: a descendant
                # of a collapsed <details> still reports a bounding rect in
                # Chromium while being unrendered and unhittable. Filtering on
                # the rect alone reported the phone's collapsed 36-topic list
                # as six controls trapped under the navigation, which is a test
                # bug wearing the costume of a layout bug.
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


class TestDiscoveredDefects:
    """Defects found in the UAT pass of 2026-08-20, encoded as the behaviour a
    learner should get.

    `strict=True` is the point: while the defect stands the suite is green and
    the defect is documented; the moment somebody fixes it, the unexpected pass
    fails the build and says "this marker is stale, delete it". A skip would
    rot silently and a plain failure would train everyone to ignore red.
    """

    def test_a_reload_keeps_you_where_you_were(self, page):
        """QA-2, fixed: the open tab is in the hash, so a refresh returns to
        it instead of dropping the learner on Rada."""
        open_tab(page, "exam", "status")
        assert page.is_visible("#tab-status")
        page.reload(wait_until="networkidle")
        page.wait_for_timeout(800)
        assert page.is_visible("#tab-status"), "reload lost the learner's place"

    def test_a_pasted_link_opens_that_tab(self, page, live_server):
        """Deep linking, which the page had no way to express before."""
        page.goto(live_server + "/#drill", wait_until="networkidle")
        page.wait_for_timeout(800)
        assert page.is_visible("#tab-drill")
        # Which nav owns the tab is asked of the page: free practice moved from
        # Eksam to Õppimine, and a hardcoded mode here would assert on where the
        # tab used to live rather than on deep linking, which is the subject.
        owner = mode_of(page, "drill")
        assert page.get_attribute(
            f'nav[data-mode-nav="{owner}"] button[data-tab="drill"]',
            "aria-selected") == "true", "the tab opened but its button is not selected"

    def test_back_returns_to_the_previous_tab_not_out_of_the_app(self, page):
        """The half of QA-2 that matters most on a phone, where Back is a
        system gesture: it used to leave the app entirely."""
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
        """The bug the hash routing itself introduced, and the reason Safari
        is in this suite.

        Opening a tab runs its `ON_OPEN` loader. Landing directly on an
        exam-mode hash ran `loadExam()` before `let examLevel` had been
        evaluated -- a temporal dead zone, in *both* engines. It stayed
        invisible because the loader is `async`, so the failure arrived as an
        unhandled rejection rather than an error anybody had subscribed to;
        the panel still rendered, so every visibility assertion passed.

        Hence both halves here: visit each tab by URL, and demand silence.
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
        """QA-2b, fixed. The level is a preference about a view, so it lives in
        localStorage rather than the learner's database, which is for things
        that were actually done."""
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

    def test_choosing_all_shows_more_than_one_difficulty(self, page):
        """QA-1, fixed: unfiltered browsing interleaves the bands instead of
        letting the newest harvest fill the whole limit."""
        open_tab(page, "learn", "read")
        page.select_option("#readLevel", "")
        page.click("#loadLib")
        page.wait_for_selector("#libList .lib-item", timeout=20000)
        bands = page.eval_on_selector_all(
            "#libList .lib-item .lib-meta",
            "els=>[...new Set(els.map(e=>e.textContent.split('·')[0].trim()))]")
        assert len(bands) > 1, f"'kõik' returned only {bands}"

class TestEveryMarkIsActuallyDrawn:
    """An icon with no dimensions is not a small icon, it is no icon.

    The nav marks were sized by `nav[data-mode-nav] .ico svg{width:16px}`
    inside `@media (min-width:720px)`. Below that width the `<svg>` had no
    width and no height and collapsed to 0x0, so the phone bar — the one this
    app is mostly used in — showed seven bare words. Nothing threw, nothing
    overflowed, and the desktop was perfect, so every check that existed
    passed.

    It is the same defect as an `<svg>` with no size rule at all rendering at
    the default 300x150, which had already been found and written down once;
    it just wears the opposite symptom when the parent gives it no basis to
    grow into. Both are only visible if something asks how big the thing
    actually came out.
    """

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
    """The whole vocabulary feature was reachable by no test.

    `renderVocabCard`, `wireGrading`, `speakWord` and the `kind === "vocab"`
    dispatch could all be deleted and the suite stayed green -- a feature with
    no caller in the test suite, which is the same shape as a measurement with
    no writer. It needs a browser because the thing worth asserting is the
    order: the ratings must not be reachable until the answer is on screen,
    and that is layout, not markup.
    """

    #: A word per viewport. `live_server` is session-scoped, so both
    #: parametrisations share one `review.db` -- and `review.add` keeps an
    #: existing item's schedule by design, so the run that grades a card leaves
    #: it not-due for the run after it. Two words, no ordering coupling. Both
    #: have identical genitive and partitive and a shipped Russian gloss, which
    #: is exactly the pair of conditions a meaning card needs.
    WORD = {"desktop": ("maja", "дом"), "phone": ("tool", "стул")}

    def _queue_a_meaning_card(self, page, live_server):
        word, _ = self.WORD[page.viewport_name]
        return page.evaluate("""async ([base, word]) => {
            const r = await fetch(base + "/api/mine", {
              method: "POST", headers: {"Content-Type": "application/json"},
              body: JSON.stringify({word, context: "See on " + word + "."}),
            });
            return await r.json();
        }""", [live_server, word])

    def test_reveal_then_rate(self, page, live_server):
        """One flow, not two tests.

        `review.add` keeps an existing item's schedule on purpose, so a card
        graded by an earlier test is no longer due for the next one -- split
        across two tests and two viewports, the fourth run found an empty
        queue. The reveal and the grade are one sequence; asserting them
        together is both more honest and free of the ordering coupling.
        """
        word, meaning = self.WORD[page.viewport_name]
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
