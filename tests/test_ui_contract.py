"""The interface asks for things; this checks the API serves them.

A whole suite passed while the reading list returned zero texts for every
difficulty. The cause was a rename: relative bands moved out of the `level`
column into their own, and the `<select>` went on sending `level=kergem`. The
API answered honestly — no item has that level any more — and the page showed
an empty list with no error.

Nothing caught it because the two halves are tested separately. `library()` was
asked for `band` and answered; the page sent `level` and nobody asked what the
page sent. This is the seam, and it is where the last three UI bugs have been:
the POST-only fetch helper, the `role="tab"` mismatch, and this.

The approach is deliberately blunt — read the page, pull out what it queries,
and demand the API accepts it. A cleverer test would have the same blind spot
as the code.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

pytest.importorskip("httpx", reason="TestClient needs httpx")

from fastapi.testclient import TestClient  # noqa: E402

from eesti import app as app_module  # noqa: E402

PAGE = Path(__file__).resolve().parent.parent / "eesti" / "web" / "index.html"


@pytest.fixture(scope="module")
def page() -> str:
    return PAGE.read_text(encoding="utf-8")


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setattr(app_module, "PROGRESS_DB", str(tmp_path / "p.db"))
    monkeypatch.setattr(app_module, "REVIEW_DB", str(tmp_path / "r.db"))
    monkeypatch.setattr(app_module, "VOCAB_DB", str(tmp_path / "v.db"))
    monkeypatch.setattr(app_module, "NOTION_DB", str(tmp_path / "n.db"))
    monkeypatch.delenv("PROXY_TOKEN", raising=False)
    return TestClient(app_module.app)


def api_paths(page: str) -> set[str]:
    """Every `/api/...` literal the page fetches, normalised to a route shape.

    Two ways the page builds a URL, and both have to survive normalisation:
    a template literal (`/api/exam/${level}`) and plain concatenation
    (`"/api/lookup/" + word`). A trailing slash means the value follows, so it
    becomes a parameter rather than being trimmed away — trimming it turned
    `/api/lookup/` into `/api/lookup` and reported a route that exists as
    missing.
    """
    # Comments are not calls. A comment explaining *why* a handler goes
    # through `/api/library/{id}` was read as a call to a route of that
    # literal name — the page should be free to name its own endpoints in
    # prose without the test inventing a caller.
    code = re.sub(r"/\*.*?\*/", " ", page, flags=re.S)
    code = re.sub(r"(?m)^\s*//.*$", " ", code)
    code = re.sub(r"<!--.*?-->", " ", code, flags=re.S)
    found = set(re.findall(r'["`\'](/api/[^"`\'?\s]+)', code))
    out = set()
    for path in found:
        path = re.sub(r"\$\{[^}]*\}", "{x}", path)
        out.add(path[:-1] + "/{x}" if path.endswith("/") else path)
    return out


class TestEveryEndpointThePageCallsExists:
    def test_no_call_is_to_a_route_that_does_not_exist(self, page):
        """A typo or a renamed route shows as an empty panel, never an error."""
        routes = {
            re.sub(r"\{[^}]+\}", "{x}", r.path).rstrip("/")
            for r in app_module.app.routes if hasattr(r, "path")
        }
        for path in api_paths(page):
            assert path in routes, f"the page calls {path}, which is not a route"


class TestQueryParametersAreAccepted:
    """The bug that made this file: the page sent a parameter the API had
    stopped using, and got an empty list rather than a complaint."""

    @pytest.mark.parametrize("query", [
        "/api/library?skill=lugemine&limit=80",
        "/api/library?skill=lugemine&band=kergem&limit=80",
        "/api/library?skill=eksam&limit=40",
        "/api/reading/next?limit=25",
    ])
    def test_the_reading_views_are_served(self, client, query):
        assert client.get(query).status_code == 200

    def test_the_difficulty_filter_uses_the_column_it_lives_in(self, page):
        """`band`, not `level`. They were one column and are now two, and the
        page kept sending the name that no longer selects anything."""
        loader = page.split("async function loadLibrary")[1][:1600]
        assert 'q.set("band"' in loader
        assert 'q.set("level"' not in loader

    def test_the_selector_offers_the_recommendation_first(self, page):
        """It is the only option that knows anything about *this* reader; the
        rest rank texts against each other."""
        options = page.split('id="readLevel"')[1][:600]
        first = re.search(r'<option value="([^"]*)"', options).group(1)
        assert first == "soovitatud"


class TestVerbsMatch:
    def test_endpoints_the_page_posts_to_accept_post(self, client):
        for path, body in [("/api/check", {"text": "Tere"}),
                           ("/api/notion/queue", {"wrong": "a", "correct": "b",
                                                  "tag": "obj-case"})]:
            assert client.post(path, json=body).status_code in (200, 400)

    def test_endpoints_the_page_gets_do_not_require_a_body(self, client):
        """The fetch helper was POST-only, and posting to a GET route produces
        a 405 that looks exactly like a feature quietly not working."""
        for path in ("/api/modes", "/api/readiness/A2", "/api/exam/A2",
                     "/api/reading/next"):
            assert client.get(path).status_code == 200, path


class TestTheDesktopRail:
    """A MacBook is the other half of this app. The rail is what fills the
    300px a phone does not have — countdown, resume point, untouched exam
    parts — and it broke once in a way no API test could see: the base
    `.rail{display:none}` sat *after* the media query, same specificity, so
    the later rule won and the rail was invisible at every width while still
    fetching and rendering into itself."""

    def test_the_hiding_rule_comes_before_the_query_that_undoes_it(self, page):
        hide = page.index(".rail{display:none}")
        query = page.index("@media (min-width:1080px)")
        assert hide < query, (
            "`.rail{display:none}` must precede the media query; at equal "
            "specificity the later declaration wins and the rail disappears"
        )

    def test_the_query_turns_the_rail_back_on(self, page):
        block = page[page.index("@media (min-width:1080px)"):][:700]
        assert "display:flex" in block.split(".rail{")[1]

    def test_the_countdown_follows_the_level_the_learner_picked(self, page):
        """Hardcoding a level here would have shown B1's countdown while the
        rest of the page was on A2 — and A2 is the nearer decision."""
        fn = page.split("async function loadRail")[1][:900]
        assert "/api/readiness/${examLevel}" in fn
        assert "/api/readiness/B1" not in fn
        assert "/api/readiness/A2" not in fn

    def test_the_rail_is_refreshed_when_what_it_shows_changes(self, page):
        """Mastered topics and due reviews both move during a session. A rail
        that only renders on load is a wrong number sitting in the corner."""
        assert page.count("loadRail()") >= 4  # load, level switch, path, review


class TestEveryTabOpensItsOwnPanel:
    """Found by opening the app on a laptop: clicking `Kirjutamine` left the
    path panel on screen.

    `TABS` was a hand-written list of panel names and it had drifted from the
    document — `path`, `speak` and `status` were missing. `selectTab` only
    hides what the list names, so `#tab-path` was never hidden (it showed
    underneath every other tab) and `#tab-speak` and `#tab-status` were never
    unhidden (the speaking practice and the progress view could not be opened
    at all). Nothing failed: every click still produced a panel, just not the
    one asked for.

    The fix derives the set from the panels themselves. These tests hold the
    two halves together whichever way the next section is added."""

    def panels(self, page: str) -> set[str]:
        return set(re.findall(r'id="tab-([a-z]+)"', page))

    def buttons(self, page: str) -> set[str]:
        return set(re.findall(r'data-tab="([a-z]+)"', page))

    def test_every_button_has_a_panel(self, page):
        missing = self.buttons(page) - self.panels(page)
        assert not missing, f"tabs with no panel: {sorted(missing)}"

    def test_every_panel_has_a_button(self, page):
        """An orphan panel is one that shows and never hides, because nothing
        ever selects a different tab within its group."""
        missing = self.panels(page) - self.buttons(page)
        assert not missing, f"panels no tab opens: {sorted(missing)}"

    def test_the_switch_set_is_read_from_the_document(self, page):
        """A literal list is what drifted. Deriving it makes adding a section
        sufficient."""
        decl = page.split("const TABS =")[1][:220]
        assert "querySelectorAll" in decl, (
            "TABS must be derived from the panels in the document, not "
            "hand-listed — the hand-listed version silently lost three panels"
        )

    def test_exactly_one_panel_starts_visible(self, page):
        """Two unhidden panels stack on load; zero shows a blank app."""
        sections = re.findall(r'<section class="panel" id="tab-[a-z]+"([^>]*)>', page)
        assert sum("hidden" not in s for s in sections) == 1


class TestTheListeningTabHasAnExercise:
    """It was a text-to-speech box: paste a passage, hear it read. Nothing
    could be answered, so nothing was scored and nothing recorded — and the
    verdict reported listening untouched however much had been played."""

    def test_the_page_calls_the_dictation_endpoints(self, page):
        for path in ("/api/dictation/next", "/api/dictation/answer"):
            assert path in page

    def test_they_answer(self, client):
        assert client.get("/api/dictation/next").status_code == 200
        assert client.post("/api/dictation/answer",
                           json={"text": "Ma elan siin.",
                                 "typed": "Ma elan siin."}).status_code == 200

    def test_the_sentence_is_not_rendered_before_it_is_answered(self, page):
        """Held in JS and written into the DOM only by the result render. A
        screen rather than a lock — devtools defeats it, and that is the
        learner's business — but it must not be on screen by accident.

        Scoped to the loader's own body. A fixed-size window spilled into the
        next function, where `dictNow.text` goes to the synthesiser and is
        exactly where it belongs."""
        body = page.split("async function loadDictation")[1]
        body = body.split("async function dictAudio")[0]
        assert "dictNow = " in body
        assert "dictNow.text" not in body, (
            "the loader must not put the sentence on screen — that is the "
            "exercise"
        )

    def test_the_player_is_not_in_the_container_the_result_overwrites(self, page):
        """It was, and grading destroyed it — so replaying while looking at the
        marked words, the moment a replay is worth most, was impossible."""
        assert 'id="dictAudio"' in page
        play = page.split('$("#dictPlay").onclick')[1][:500]
        assert '$("#dictAudio")' in play
        assert '$("#dictOut")' not in play

    def test_grading_is_server_side(self, page):
        """A page can be edited; a score the browser computed measures
        nothing. The same rule the practice loop follows."""
        check = page.split('$("#dictCheck").onclick')[1][:700]
        assert "/api/dictation/answer" in check


class TestATwoChoiceItemIsAnsweredByChoosing:
    """Word order is the one topic whose unit is the whole sequence, so its
    items carry `choices` instead of a blank. Everything downstream is
    unchanged — the chosen sentence is submitted as the answer and the server
    grades it the same way — which is what lets it reach mastery and the review
    queue without a loop of its own."""

    def test_the_renderer_has_a_branch_for_them(self, page):
        assert "it.choices && it.choices.length" in page

    def test_the_chosen_sentence_is_what_gets_submitted(self, page):
        fn = page.split("function renderPracticeItem")[1]
        assert "given: input ? input.value : picked" in fn

    def test_the_typed_path_still_exists_for_every_other_item(self, page):
        fn = page.split("function renderPracticeItem")[1]
        assert 'input type="text"' in fn
        assert 'e.key === "Enter"' in fn

    def test_a_correct_choice_does_not_echo_the_question(self, page):
        """The blank-filling verdict fills `____` from the prompt. A choice
        item's prompt is a question with no blank, so that path printed
        "✓ õige — Kumb lause on õige?" back at the learner."""
        fn = page.split("verdict.innerHTML = res.correct")[1][:600]
        assert "choices.length" in fn

    def test_choosing_locks_both_buttons(self, page):
        """Otherwise the second click would submit a second answer for an item
        already graded, and the accuracy gate would count it."""
        fn = page.split("const lock = ()")[1][:300]
        assert "disabled = true" in fn


class TestEverySectionCanBeReached:
    """This file has checked one direction since it was written: every
    endpoint the page calls must exist. The other direction was never checked,
    and that is where 82 items went missing.

    Two of the seven library sections — the entire harvested listening archive
    (54 items) and the 28 radio-course transcripts, 13 % of everything
    harvested — were indexed, sectioned, and covered by API tests, and could
    not be opened from the app. The page could only ask the library by *skill*,
    and it only ever asked for `lugemine`.

    It cost more than hidden content: the readiness verdict measures Kuulamine
    by library items opened, so that evidence could never move."""

    def test_the_page_can_ask_for_every_learning_section(self, page, client):
        from eesti.library import SECTIONS

        learn = [s for s in SECTIONS if s.mode == "oppimine"]
        assert learn, "the fixture is wrong, not the app"
        # Either named directly, or reachable because the page renders whatever
        # /api/modes returns.
        driven = "/api/modes" in page and "section=" in page
        for section in learn:
            assert driven or section.id in page, (
                f"section {section.id!r} cannot be reached from the page"
            )

    def test_the_library_endpoint_serves_a_section(self, client):
        assert client.get("/api/library?section=kuulamine").status_code == 200
        assert client.get("/api/library?section=saated").status_code == 200

    def test_an_unknown_section_is_a_404_not_an_empty_list(self, client):
        """An empty list would look exactly like a section with no material,
        which is a supported state — a typo must not imitate it."""
        assert client.get("/api/library?section=nope").status_code == 404

    def test_the_modes_endpoint_has_a_caller_now(self, page):
        """It returned every section with its count and its Russian note, and
        nothing called it. An endpoint with no caller is the same shape of bug
        as a measurement with no writer."""
        assert "/api/modes" in page

    def test_opening_a_listening_item_records_it(self, page):
        """Mounting a player straight from the list row would look identical
        and leave the verdict at zero. It has to go through the endpoint that
        writes the exposure down."""
        fn = page.split("async function openListenItem")[1][:900]
        assert "/api/library/" in fn


class TestAPointerIsALinkNotAPlayer:
    """Ten of the listening shelf's items are EIS tasks: their audio and their
    scoring live on eis.harno.ee, and nothing of theirs is stored here — `body`
    is empty and there is no `audio_url`, by licence and by design.

    Rendered as expandable rows they opened on an empty panel. The exam section
    had already made this distinction; the new listening list had to make it
    too, which is the cost of a second list rather than a shared one."""

    def test_the_api_marks_them(self, monkeypatch, tmp_path):
        """Built here rather than read from a harvest: a test that only passes
        where the corpus happens to exist is a test that fails in CI for the
        wrong reason."""
        from fastapi.testclient import TestClient

        from eesti import app as app_module, config
        from eesti.sources import Item, add_items, connect, register

        path = tmp_path / "content.db"
        conn = connect(path)
        register(conn)
        add_items(conn, [
            Item(source_id="eis", skill="kuulamine", level="A2",
                 title="Kuulamine 1 (A2-tase, harjutusülesanne)",
                 body="",                       # nothing of theirs is stored
                 meta={"external": True,
                       "url": "https://eis.harno.ee/publicitems/54950"}),
            Item(source_id="err-r4", skill="kuulamine", title="Saade",
                 body="Tere. See on tekst.", audio_url="https://example/a.mp3"),
        ])
        conn.commit()
        monkeypatch.setattr(config, "CONTENT_DB", str(path))

        got = TestClient(app_module.app).get(
            "/api/library?section=kuulamine&limit=100").json()
        external = [i for i in got["items"] if i.get("external")]
        assert len(external) == 1
        assert external[0]["url"].startswith("https://eis.harno.ee/")
        # And the one with real content is not flagged, or it would lose its
        # player.
        assert any(not i.get("external") for i in got["items"])

    def test_the_page_branches_on_it(self, page):
        fn = page.split("async function loadListenLibrary")[1][:2000]
        assert "it.external" in fn
        assert 'target="_blank"' in fn

    def test_only_real_content_gets_a_click_handler(self, page):
        """Binding the handler to every row would put an expander on a link."""
        fn = page.split("async function loadListenLibrary")[1][:2000]
        assert '.lib-item[data-id]' in fn
