"""EstGEC-L2: labelled word-order errors, merged with the inferred ones.

The M2 fixture is written for the test in the corpus's real shape (`S` and `A`
lines, `|||`-separated fields, `noop`, overlapping spans); every sentence is
invented.
"""

from __future__ import annotations

import pytest

from eesti import estgec, wordorder

# Sentence 1: word order only, and the drill's ideal shape.
# Sentence 2: word order plus a verb-form error — must not become an item.
# Sentence 3: nothing wrong.
# Sentence 4: word order that also changes a case (R:WO:NOM:FORM).
# Sentence 5: two annotators, so the second must not produce a second item.
M2 = """S Eile ma läksin kooli .
A 1 3|||R:WO|||läksin ma|||REQUIRED|||-NONE-|||0

S Ma sulle helistan homme tegema .
A 1 3|||R:WO|||helistan sulle|||REQUIRED|||-NONE-|||0
A 4 5|||R:VERB:FORM|||teen|||REQUIRED|||-NONE-|||0

S See on ilus maja .
A -1 -1|||noop|||-NONE-|||REQUIRED|||-NONE-|||0

S See on pealinn Islandil .
A 2 4|||R:WO:NOM:FORM|||Islandi pealinn|||REQUIRED|||-NONE-|||0

S Alati mina joon kohvi .
A 1 3|||R:WO|||joon mina|||REQUIRED|||-NONE-|||0
A 1 3|||R:WO|||mina joon|||REQUIRED|||-NONE-|||1
"""


@pytest.fixture
def m2(tmp_path):
    """Written under the name the cache uses, so `pairs()` finds it the way it
    finds a real download — `test/A2/A2_source_gold.txt` flattened."""
    path = tmp_path / "test_A2_A2_source_gold.txt"
    path.write_text(M2, encoding="utf-8")
    return path


class TestReadingTheirM2:
    def test_a_word_order_only_sentence_becomes_a_pair(self, m2):
        got = estgec.parse(m2, "A2")
        assert ("Eile ma läksin kooli.", "Eile läksin ma kooli.", "A2") in got

    def test_a_sentence_with_another_error_beside_it_is_not_taken(self, m2):
        """The two options would then differ in more than order, and the
        learner could answer on the verb instead."""
        assert not any("helistan" in w for w, _, _ in estgec.parse(m2))

    def test_a_sentence_that_needed_nothing_is_not_an_item(self, m2):
        assert not any("ilus maja" in w for w, _, _ in estgec.parse(m2))

    def test_only_the_first_annotator_is_read(self, m2):
        """The corpus carries up to three parallel annotations of one sentence.
        Reading all of them would offer the same item repeatedly with different
        right answers."""
        got = [p for p in estgec.parse(m2) if "kohvi" in p[0]]
        assert len(got) == 1
        assert got[0][1] == "Alati joon mina kohvi."

    def test_the_level_rides_along(self, m2):
        assert {lvl for _, _, lvl in estgec.parse(m2, "B1")} == {"B1"}

    def test_a_file_that_was_never_fetched_is_empty_not_an_error(self, tmp_path):
        assert estgec.parse(tmp_path / "absent.txt") == []


class TestTheSentencesReadLikeSentences:
    def test_tokenisation_is_undone(self, m2):
        """M2 is tokenised — `kooli .` — and the drill shows both sentences to
        the learner. The space is visible, identical in both options, and
        therefore teaches nothing while looking wrong."""
        for wrong, right, _ in estgec.parse(m2):
            assert " ." not in wrong and " ." not in right
            assert " ," not in wrong and " ," not in right

    def test_a_comma_still_attaches_to_the_word_before_it(self):
        assert estgec._detokenize(["Ma", "loodan", ",", "et", "ta", "tuleb", "."]) \
            == "Ma loodan, et ta tuleb."


class TestOneGateTwoFeeders:
    """Both sources feed one pool through the same `is_reordering` gate."""

    def test_both_sources_are_drawn_from(self):
        assert wordorder.SOURCE_IDS == ("taltech-gec", "estgec-l2")

    def test_a_case_changing_reorder_is_still_refused(self, m2):
        """`pealinn Islandil` -> `Islandi pealinn` is a labelled `R:WO`, and it
        changes a case ending too. A label does not exempt a pair from the gate:
        the learner could answer this one from the ending."""
        pair = next(p for p in estgec.parse(m2) if "Islandil" in p[0])
        assert not wordorder.is_reordering(pair[0], pair[1])
        assert not any(i.wrong == pair[0] for i in wordorder.from_pairs([pair]))

    def test_a_clean_one_passes(self, m2):
        pair = next(p for p in estgec.parse(m2, "A2") if "Eile" in p[0])
        items = wordorder.from_pairs([pair])
        assert len(items) == 1
        assert items[0].level == "A2"
        assert items[0].rule == "v2", "the fronted adverbial and the verb second"

    def test_a_pair_with_no_level_is_still_an_item(self):
        """The dev split has no level, so its items carry `None`."""
        items = wordorder.from_pairs([("Eile ma tulin.", "Eile tulin ma.")])
        assert len(items) == 1 and items[0].level is None


class TestTheyReachTheDrillTogether:
    def test_items_from_both_sources_come_back(self, tmp_path, m2):
        from eesti.sources import connect

        conn = connect(tmp_path / "content.db")
        wordorder.ingest_estgec(conn, m2.parent)
        # A TalTech-shaped pair through the other door.
        from eesti.sources import Item as SourceItem
        from eesti.sources import add_items
        add_items(conn, [SourceItem(
            source_id="taltech-gec", skill="kirjutamine",
            body="Eile tulin ma koju.", title="sõnajärg: v2",
            meta={"wrong": "Eile ma tulin koju.", "rule": "v2", "tag": "word-order"})])

        got = wordorder.items(conn, limit=100)
        assert len(got) >= 2
        assert any(i.level == "A2" for i in got), "the levelled one survived"
        assert any(i.level is None for i in got), "and the unlevelled one"

    def test_the_level_survives_the_round_trip(self, tmp_path, m2):
        from eesti.sources import connect

        conn = connect(tmp_path / "content.db")
        wordorder.ingest_estgec(conn, m2.parent)
        levels = {i.level for i in wordorder.items(conn, limit=100)}
        assert "A2" in levels

    def test_ingesting_twice_adds_nothing(self, tmp_path, m2):
        from eesti.sources import connect

        conn = connect(tmp_path / "content.db")
        first = wordorder.ingest_estgec(conn, m2.parent)
        wordorder.ingest_estgec(conn, m2.parent)
        assert len(wordorder.items(conn, limit=100)) == first


class TestTheLicenceIsRecorded:
    def test_the_source_is_in_the_ledger(self):
        from eesti.sources import REGISTRY

        entry = next(s for s in REGISTRY if s.id == estgec.SOURCE_ID)
        assert entry.licence == "GPL-3.0"
        assert not entry.redistributable, "conveyed to nobody, so nothing to convey"
