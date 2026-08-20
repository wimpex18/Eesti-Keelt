"""One cleaner for four harvesters, and the three defects that came of four.

Each harvester carried its own `_TAG_RE = re.compile(r"<[^>]+>")` and its own
idea of what else to do with it. On one line of input they produced three
different answers, and every difference reached the learner:

  * `err.py` never decoded entities, so `&#8211;` appeared as literal
    characters in 27 000 words of transcript — the richest text in the corpus,
    and reachable from the app since the listening shelf was wired up;
  * `evkk.py` replaced tags with nothing rather than a space, so
    `<p>Esimene</p><p>Teine</p>` became the single word `EsimeneTeine`;
  * all four left a space before a full stop wherever an inline tag had been,
    which the punctuation drill then showed as correct Estonian.
"""

from __future__ import annotations

import pytest

from eesti.harvest.clean import text


class TestTheThreeDefects:
    def test_entities_are_decoded(self):
        assert text("<p>Eesti &#8211; ilus maa.</p>") == "Eesti – ilus maa."

    def test_double_encoded_entities_are_decoded_too(self):
        """WordPress does this, which is where the second pass came from."""
        assert text("<p>Eesti &amp;#8211; ilus.</p>") == "Eesti – ilus."

    def test_a_tag_between_two_words_does_not_join_them(self):
        assert text("<p>Esimene</p><p>Teine</p>") == "Esimene Teine"

    def test_no_space_is_left_before_punctuation(self):
        got = text('<p>Vaata <a href="https://err.ee/x">siit</a>.</p>')
        assert got == "Vaata siit."
        assert " ." not in got

    @pytest.mark.parametrize("mark", [".", ",", "!", "?", ";", ":"])
    def test_for_every_mark_that_closes_up(self, mark):
        assert text(f"<p>sõna <b>teine</b>{mark}</p>") == f"sõna teine{mark}"


class TestWhatItMustNotBreak:
    def test_a_bare_ampersand_survives(self):
        """Decoding twice must not eat text that is not an entity."""
        assert text("<p>Fish &amp; Chips</p>") == "Fish & Chips"

    def test_urls_go_by_default(self):
        """The reader makes every word clickable, and `kultuur`, `err`, `ee`
        are not Estonian words."""
        assert "err.ee" not in text("<p>Vaata https://err.ee/x lehte.</p>")

    def test_but_can_be_kept_where_the_address_is_the_content(self):
        assert "err.ee" in text("<p>https://err.ee/x</p>", drop_urls=False)

    def test_opening_brackets_close_up_too(self):
        assert text("<p>mis on ( siin ) ?</p>") == "mis on (siin)?"

    def test_empty_input_is_empty_output(self):
        assert text("") == "" and text(None) == ""


class TestNobodyKeepsAPrivateCopy:
    """The root cause was four copies, not any one of the three bugs."""

    def test_no_harvester_defines_its_own_tag_regex(self):
        from pathlib import Path

        root = Path(__file__).resolve().parent.parent / "eesti" / "harvest"
        for path in root.glob("*.py"):
            if path.name == "clean.py":
                continue
            body = path.read_text(encoding="utf-8")
            assert '<[^>]+>' not in body, (
                f"{path.name} strips tags itself; use harvest/clean.py"
            )
