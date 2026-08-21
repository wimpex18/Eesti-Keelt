"""How the meaning is presented, which is most of whether it helps.

The store landed first and the screen got the leftovers: one 12px grey line,
`protsent, osastav — процент · A2`, four kinds of information joined by three
different separators at one weight. The word you operate on, the form to
produce, what the word means and where it sits on the CEFR scale all looked
identical, and the new information — the meaning — was the least visible thing
on the card.

Four roles, four treatments, and one token for the one that was missing.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

PAGE = (Path(__file__).resolve().parent.parent
        / "eesti" / "web" / "index.html").read_text(encoding="utf-8")


class TestTheInstructionIsNotOneGreyRunOn:
    def test_the_parts_are_rendered_separately(self):
        for part in ('class="word"', 'class="form"', 'class="gloss"',
                     'class="lvl"'):
            assert part in PAGE, part

    def test_every_drill_shape_uses_the_same_component(self):
        """Typed answers, sentence choices and review cards are three call
        sites. Three copies of the layout is how one of them drifts."""
        assert PAGE.count("taskLine(") >= 4

    def test_the_component_is_defined_before_nothing_else_needs_it(self):
        assert "function taskLine(" in PAGE

    def test_the_old_run_on_is_gone(self):
        assert 'esc(it.hint || it.lemma || "")' not in PAGE


class TestBothHalvesOfTheHintAreAvailable:
    """`hint` glues lemma and label together, so a page that wants them apart
    needs the label on its own. Every generator gets it from the mixin —
    except `Cloze`, which predates the mixin and carries a private copy of the
    whole surface. That went unnoticed until cloze items came back with the
    case missing from the row."""

    def test_the_mixin_hands_out_a_label(self):
        from eesti import drills, wordlist

        item = drills.generate(wordlist.connect(), count=1, seed=1)[0].to_dict()
        assert item["label"] and item["label"] in item["hint"]

    def test_cloze_hands_out_a_label_too(self):
        from eesti.cloze import Cloze

        item = Cloze(prompt="Ma ostsin ____.", answer="kleiti", distractor="kleidi",
                     lemma="kleit", case="sg p", case_et="osastav",
                     rule="case-form", why_ru="", topic="osastav", level="A2",
                     source_id="x")
        assert item.to_dict()["label"] == "osastav"

    def test_a_rection_item_never_names_the_case(self):
        """For rection the case *is* the question. Printing it in the task row
        would put the answer above the prompt."""
        from eesti.cloze import Cloze

        item = Cloze(prompt="Ma ____ sellega.", answer="kohanen", distractor="",
                     lemma="kohanema", case="sg kom", case_et="kaasaütlev",
                     rule="rection", why_ru="", topic="rektsioon", level="B1",
                     source_id="x", governor="millega")
        assert "kaasaütlev" not in item.label
        assert item.label == "millega?"


class TestTheGlossHasItsOwnColour:
    """A verdict answers three questions at once — what the right form was, why
    the rule made it right, and what the word is. The first two had colours;
    the third arrived as more grey prose and read as part of the rule."""

    def test_the_token_exists(self):
        assert "--gloss:" in PAGE

    def test_it_is_defined_in_every_theme_state(self):
        """Three states, not two: an explicit choice stamps `data-theme`, and
        the default 'system' setting stamps nothing at all. A colour whose only
        definition sits behind a media query is invisible in the third."""
        assert PAGE.count("--gloss:#") == 3

    def test_the_light_definition_is_on_bare_root(self):
        root = PAGE.split(":root{", 1)[1].split("}", 1)[0]
        assert "--gloss:" in root

    def test_the_dark_media_query_redefines_it(self):
        block = PAGE.split("@media (prefers-color-scheme:dark)", 1)[1][:600]
        assert "--gloss:" in block

    def test_the_explicit_toggle_redefines_it(self):
        block = PAGE.split(':root[data-theme="dark"]', 1)[1][:600]
        assert "--gloss:" in block

    def test_every_gloss_surface_uses_the_token(self):
        for rule in (".task .gloss{", ".gloss-late{"):
            body = PAGE.split(rule, 1)[1].split("}", 1)[0]
            assert "var(--gloss)" in body, rule

    def test_the_rule_explanation_stays_muted(self):
        """Deliberately not colour-by-language. The rule prose is Russian too;
        painting it the same would make the rule and the meaning identical,
        which is the confusion the token exists to remove."""
        why = PAGE.split("  .why{", 1)[1].split("}", 1)[0]
        assert "var(--muted)" in why and "var(--gloss)" not in why


class TestTheQueueDoesNotPrintDatabaseKeys:
    """`obj-case` is a curriculum id. The path panel already resolves those —
    `overview.py` does it for exactly this reason — and the review queue was
    still printing the raw key beside every card, in accented capitals wider
    than the word it described."""

    def test_the_endpoint_resolves_the_name(self):
        from eesti.app import _topic_name

        assert _topic_name("obj-case") == "täissihitis ja osasihitis"
        assert _topic_name("osastav") == "osastav kääne"

    def test_an_unknown_kind_is_not_an_error(self):
        from eesti.app import _topic_name

        assert _topic_name("vocab") == "vocab"

    def test_the_queue_ships_the_readable_name(self, tmp_path, monkeypatch):
        from fastapi.testclient import TestClient

        from eesti import app as app_module

        monkeypatch.setattr(app_module, "VOCAB_DB", str(tmp_path / "v.db"))
        monkeypatch.setattr(app_module, "REVIEW_DB", str(tmp_path / "r.db"))
        client = TestClient(app_module.app)
        client.post("/api/review", json={
            "kind": "obj-case", "lemma": "kleit", "prompt": "Ma ostsin ____.",
            "answer": "kleidi"})
        got = client.get("/api/review?limit=5").json()["items"][0]
        assert got["kind_et"] == "täissihitis ja osasihitis"

    def test_the_page_prefers_the_readable_name(self):
        assert "it.kind_et || it.kind" in PAGE

    def test_a_topic_name_is_provenance_not_an_instruction(self):
        """In a practice set the label says what to produce and earns the
        accent. In the queue it says which lesson filed the card, which is a
        different thing and gets the quiet chip."""
        assert "{quiet: true}" in PAGE


class TestTheCountHasAReader:
    """`gloss.stats` was written with nothing calling it, which is the same
    defect as a measurement with no writer."""

    def test_the_overview_carries_it(self, tmp_path):
        from eesti import gloss, overview, vocab
        from eesti.providers import sonapi
        from eesti.wordlist import connect as wordlist_connect

        path = tmp_path / "v.db"
        # Without the shipped glossary: this asserts that *one* saved gloss is
        # counted, and 294 seeded rows would make the number about the file.
        store = gloss.connect(path, seed_glosses=False)
        gloss.save(store, "kleit", sonapi.WordInfo(
            word="kleit", word_classes=(), rection=None, inflection_type="2",
            definition=None, examples=(), translations={"ru": ("платье",)}))
        data = overview.overview(vocabulary=vocab.connect(path),
                                 words=wordlist_connect())
        assert data["sections"]["sonavara"]["glossed"] == 1

    def test_an_older_database_without_the_table_is_not_an_error(self, tmp_path):
        import sqlite3

        from eesti import overview

        conn = sqlite3.connect(tmp_path / "old.db")
        conn.row_factory = sqlite3.Row
        assert overview._gloss_line(conn) == {} or "glossed" in overview._gloss_line(conn)

    def test_the_page_renders_it(self):
        assert "s.sonavara.glossed" in PAGE

    def test_it_is_kept_apart_from_known_words(self):
        """Two different facts. "Known" is what the learner declared; this is
        what the app can translate for them, and it grows on its own."""
        assert "known_in_top" in PAGE and "s.sonavara.glossed" in PAGE
        block = PAGE.split("s.sonavara.glossed", 1)[1][:400]
        assert "gloss-late" in PAGE.split("s.sonavara.glossed", 1)[0][-200:] or \
               "gloss-late" in block


class TestTheWordCardPutsMeaningWithTheWord:
    """The enrichment arrives after the card is drawn and has to be inserted
    somewhere. It went in before `#mineNote`, which sits *under* the buttons —
    so what the word means appeared below "+ Kordamisse", after the actions
    rather than beside the word they act on."""

    def test_there_is_an_anchor_above_the_buttons(self):
        assert 'id="cardExtra"' in PAGE
        head = PAGE.split('id="cardExtra"', 1)[1].split('id="mineNote"', 1)[0]
        assert 'id="mineBtn"' in head, "the anchor is not above the button row"

    def test_the_enrichment_uses_it(self):
        assert 'card.querySelector("#cardExtra")' in PAGE

    def test_nothing_still_inserts_before_the_note(self):
        assert '#mineNote").before(' not in PAGE


class TestEveryGeneratorSharesOneDefinition:
    """`item.GradedItem` exists because each generator kept its own copy of the
    same five methods, and copies drift. `Cloze` predated the mixin and was
    still carrying all five — which is how a cloze item reached the page with
    no case in its instruction row, months after every other generator had been
    unified.

    A one-off fix would have been `label`. The bug was the copies."""

    @staticmethod
    def _shaped():
        """Every dataclass that is an exercise item."""
        import dataclasses
        import importlib
        import inspect

        found = []
        for name in ("cloze", "drills", "conjugation", "patterns",
                     "punctuation", "wordorder"):
            module = importlib.import_module(f"eesti.{name}")
            for cls in vars(module).values():
                if (inspect.isclass(cls) and dataclasses.is_dataclass(cls)
                        and cls.__module__ == module.__name__):
                    fields = {f.name for f in dataclasses.fields(cls)}
                    if {"prompt", "answer", "lemma", "topic"} <= fields:
                        found.append(cls)
        return found

    def test_there_are_generators_to_check(self):
        assert len(self._shaped()) >= 5

    def test_every_item_class_uses_the_mixin(self):
        from eesti.item import GradedItem

        rogue = [c.__name__ for c in self._shaped()
                 if not issubclass(c, GradedItem)]
        assert not rogue, f"carrying private copies of the item surface: {rogue}"

    def test_none_of_them_reimplements_grading(self):
        """`check`, `solution`, `reference` and `to_dict` are the four that must
        not vary. `hint` and `label` legitimately do — rection asks the case
        rather than naming it."""
        for cls in self._shaped():
            own = {n for n in ("check", "solution", "reference", "to_dict")
                   if n in vars(cls)}
            assert not own, f"{cls.__name__} reimplements {sorted(own)}"

    def test_every_item_class_names_the_form_it_asks_for(self):
        for cls in self._shaped():
            assert "label" in dir(cls), f"{cls.__name__} has no label"

    def test_there_is_one_blank(self):
        """A second literal is the same duplication as the four private tag
        regexes that gave one line of input three different answers."""
        from eesti import cloze, item

        assert cloze.BLANK is item.BLANK

    def test_cloze_grades_exactly_as_it_did(self):
        """Measured over 425 real items before the copies were removed:
        `lower` and `casefold` differ on no Estonian answer, and no prompt can
        open with the blank because the round-trip gate rejects a capitalised
        common noun."""
        from eesti.cloze import Cloze

        item = Cloze(prompt="Ma ostsin ____.", answer="kleidi", distractor="kleiti",
                     lemma="kleit", case="sg g", case_et="omastav",
                     rule="case-form", why_ru="", topic="obj-case", level="A2",
                     source_id="x")
        assert item.check("  KLEIDI ") and not item.check("kleiti")
        assert item.solution == "Ma ostsin kleidi."

    def test_rection_still_asks_rather_than_tells(self):
        from eesti.cloze import Cloze

        item = Cloze(prompt="Ma ____ sellega.", answer="kohanen", distractor="",
                     lemma="kohanema", case="sg kom", case_et="kaasaütlev",
                     rule="rection", why_ru="", topic="rektsioon", level="B1",
                     source_id="x", governor="millega")
        assert item.hint == "kohanema — millega?"
        assert "kaasaütlev" not in item.hint
