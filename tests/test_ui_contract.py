"""The interface asks for things; this checks the API serves them.

The page and the API are tested separately elsewhere, so this reads what the
page actually requests (routes, parameters, methods) and demands the API accepts
it.
"""

from __future__ import annotations

import re

import pytest

pytest.importorskip("httpx2", reason="TestClient needs the httpx2 transport")

from fastapi.testclient import TestClient  # noqa: E402

from eesti import app as app_module  # noqa: E402

from pagesrc import (JS, function_body, markup, markup_and_script,
                     media_block, scripts, styles)



@pytest.fixture(scope="module")
def page() -> str:
    return markup_and_script()


@pytest.fixture
def client(monkeypatch, tmp_path):
    # Redirected on `config`: every database in the app is resolved from there
    # when it is opened, and `eesti.app` only re-exports the names.
    from eesti import config

    for name, stem in (("PROGRESS_DB", "p"), ("REVIEW_DB", "r"),
                       ("VOCAB_DB", "v"), ("NOTION_DB", "n")):
        monkeypatch.setattr(config, name, str(tmp_path / f"{stem}.db"))
    monkeypatch.delenv("PROXY_TOKEN", raising=False)
    return TestClient(app_module.app)


def api_paths(page: str) -> set[str]:
    """Every `/api/...` literal the page fetches, normalised to a route shape.

    Handles template literals (`/api/exam/${level}`) and concatenation
    (`"/api/lookup/" + word`); a trailing slash means a parameter follows.
    """
    # Comments are not calls: strip them before collecting endpoints.
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
        from eesti import api

        routes = {
            re.sub(r"\{[^}]+\}", "{x}", path).rstrip("/")
            for path in api.paths(app_module.app)
        }
        for path in api_paths(page):
            assert path in routes, f"the page calls {path}, which is not a route"


class TestQueryParametersAreAccepted:
    """The page sends parameters the API still reads (an unknown parameter returns an
    empty list rather than an error).
    """

    @pytest.mark.parametrize("query", [
        "/api/library?skill=lugemine&limit=80",
        "/api/library?skill=lugemine&band=kergem&limit=80",
        "/api/library?skill=eksam&limit=40",
        "/api/reading/next?limit=25",
    ])
    def test_the_reading_views_are_served(self, client, query):
        assert client.get(query).status_code == 200

    def test_the_difficulty_filter_uses_the_column_it_lives_in(self, page):
        """The reading filter sends `band`, not `level`; the function body is sliced to its
        end rather than a fixed window.
        """
        after = page.split("async function loadLibrary")[1]
        loader = after.split("\nasync function ")[0].split("\nfunction ")[0]
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
        """GET routes are fetched with GET (posting to them would 405 silently)."""
        for path in ("/api/modes", "/api/readiness/A2", "/api/exam/A2",
                     "/api/reading/next"):
            assert client.get(path).status_code == 200, path


class TestTheDesktopRail:
    """The desktop rail: its hiding rule must precede the media query that shows it
    (same specificity, so order decides).
    """

    def test_the_hiding_rule_comes_before_the_query_that_undoes_it(self, page):
        css = styles()
        hide = css.index(".rail{display:none}")
        query = css.index("@media (min-width:1080px)")
        assert hide < query, (
            "`.rail{display:none}` must precede the media query; at equal "
            "specificity the later declaration wins and the rail disappears"
        )

    def test_the_query_turns_the_rail_back_on(self, page):
        # Search the whole media block, not a fixed-size prefix.
        block = media_block(styles(), "@media (min-width:1080px)")
        assert "display:flex" in block.split(".rail{")[1]

    def test_the_countdown_follows_the_level_the_learner_picked(self, page):
        """The countdown follows the level the learner selected."""
        fn = page.split("async function loadRail")[1][:900]
        assert "/api/readiness/${examLevel()}" in fn
        assert "/api/readiness/B1" not in fn
        assert "/api/readiness/A2" not in fn

    def test_the_rail_is_refreshed_when_what_it_shows_changes(self, page):
        """The rail re-renders when mastery or due reviews change."""
        assert page.count("loadRail()") >= 4  # load, level switch, path, review


class TestEveryTabOpensItsOwnPanel:
    """Tabs and panels correspond in both directions, derived from the document, so
    every panel can be shown and hidden.
    """

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
    """Listening has a gradeable exercise (dictation), and the page calls its
    endpoints.
    """

    def test_the_page_calls_the_dictation_endpoints(self, page):
        for path in ("/api/dictation/next", "/api/dictation/answer"):
            assert path in page

    def test_they_answer(self, client):
        assert client.get("/api/dictation/next").status_code == 200
        assert client.post("/api/dictation/answer",
                           json={"text": "Ma elan siin.",
                                 "typed": "Ma elan siin."}).status_code == 200

    def test_the_sentence_is_not_rendered_before_it_is_answered(self, page):
        """The dictation sentence is not rendered before it is answered (scoped to the
        loader's body).
        """
        body = page.split("async function loadDictation")[1]
        body = body.split("async function dictAudio")[0]
        assert "dictNow = " in body
        assert "dictNow.text" not in body, (
            "the loader must not put the sentence on screen — that is the "
            "exercise"
        )

    def test_the_player_is_not_in_the_container_the_result_overwrites(self, page):
        """The player is outside the result container, so replay works while reviewing the
        marked words.
        """
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
    """Word-order items render `choices` and submit the chosen sentence for normal
    server-side grading.
    """

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
    """The page can reach every library section the API serves (the other direction of
    the contract).
    """

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
        """`/api/modes` has a caller."""
        assert "/api/modes" in page

    def test_opening_a_listening_item_records_it(self, page):
        """Mounting a player straight from the list row would look identical
        and leave the verdict at zero. It has to go through the endpoint that
        writes the exposure down."""
        fn = page.split("async function openListenItem")[1][:900]
        assert "/api/library/" in fn


class TestAPointerIsALinkNotAPlayer:
    """EIS tasks in the listening list render as outbound links, not empty readers
    (`body` is empty and there is no `audio_url` by licence).
    """

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
        fn = function_body(page, "async function loadListenLibrary")
        assert "it.external" in fn
        assert 'target="_blank"' in fn

    def test_only_real_content_gets_a_click_handler(self, page):
        """Binding the handler to every row would put an expander on a link."""
        fn = function_body(page, "async function loadListenLibrary")
        assert '.lib-item[data-id]' in fn


class TestNoTwoElementsShareAnId:
    """No duplicated element ids: `$("#x")` returns the first match and would silently
    bind to the wrong element.
    """

    def test_every_id_in_the_markup_is_unique(self, page):
        import collections

        markup = page.split("<script>")[0]
        counts = collections.Counter(re.findall(r'\bid="([^"]+)"', markup))
        dupes = {i: n for i, n in counts.items() if n > 1}
        assert not dupes, f"duplicated ids: {dupes}"

    def test_the_two_check_buttons_are_distinct(self, page):
        """Named because they are the pair that collided, and because
        "Kontrolli" (check this writing) and "Kontrolltöö" (sit the level
        checkpoint) are genuinely different things a learner does."""
        assert 'id="checkBtn"' in page and 'id="checkpointBtn"' in page


class TestEveryModuleIsReachableFromTheEntryPoint:
    """Every module is reachable from `main.js`'s import graph; an unimported module
    never runs its wiring.
    """

    @staticmethod
    def _graph() -> dict[str, set[str]]:
        edges = {}
        for path in scripts():
            src = path.read_text(encoding="utf-8")
            edges[path.stem] = (set(re.findall(r'from "\./(\w+)\.js"', src))
                                | set(re.findall(r'import "\./(\w+)\.js"', src)))
        return edges

    def test_the_page_loads_exactly_one_module(self):
        entries = re.findall(r'<script type="module" src="([^"]+)"', markup())
        assert entries == ["/js/main.js"], entries

    def test_every_module_is_reachable(self):
        edges = self._graph()
        assert "main" in edges, "no entry point on disk"
        seen, stack = set(), ["main"]
        while stack:
            name = stack.pop()
            if name in seen:
                continue
            seen.add(name)
            stack += sorted(edges.get(name, ()))
        orphans = sorted(set(edges) - seen)
        assert not orphans, (
            f"nothing imports {orphans} — on the page these files never "
            f"evaluate, so whatever they wire up is dead and says nothing")

    def test_no_module_imports_something_that_is_not_there(self):
        edges = self._graph()
        for name, deps in edges.items():
            missing = sorted(d for d in deps if not (JS / f"{d}.js").exists())
            assert not missing, f"{name}.js imports {missing}, which do not exist"
