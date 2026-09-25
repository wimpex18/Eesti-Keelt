"""Word order: attested items, and the refusals that keep them sound.

Estonian word order is flexible, so a generated distractor is sometimes correct
Estonian; items come from attested learner/native pairs that only re-order.
"""

from __future__ import annotations

import json

import pytest

from eesti import wordorder


@pytest.fixture
def pairs():
    """Attested (learner wrote, native corrected) pairs, hand-picked from
    `grammar_et` so the test does not need the download."""
    return [
        # V2: the verb pulled into second position after a fronted adverbial.
        ("Oktoobris vihmased päevad vahelduvad kirgastega.",
         "Oktoobris vahelduvad vihmased päevad kirgastega."),
        # A native's re-ordering with no rule behind it.
        ("Praegu on talv ja minu esimene semester varsti lõpeb.",
         "Praegu on talv ja minu esimene semester lõpeb varsti."),
        # Not a re-ordering: words changed.
        ("Kellena küll saaksin?", "Kelleks küll saaksin?"),
    ]


class TestOnlyReorderingsAreKept:
    def test_a_changed_word_is_not_a_word_order_error(self, pairs):
        assert not wordorder.is_reordering(*pairs[2])

    def test_same_words_in_a_different_sequence_is(self, pairs):
        assert wordorder.is_reordering(*pairs[0])

    def test_an_identical_pair_is_not_an_error_at_all(self):
        assert not wordorder.is_reordering("Ma elan siin.", "Ma elan siin.")

    def test_the_filter_survives_punctuation_and_case(self):
        assert not wordorder.is_reordering("Ma elan siin.", "ma elan siin")

    def test_items_are_built_only_from_the_reorderings(self, pairs):
        items = wordorder.from_pairs(pairs)
        assert len(items) == 2

    def test_a_pair_that_also_moves_a_comma_is_not_kept(self):
        """Pairs that also change punctuation are refused: the comma would give the answer
        away.
        """
        assert not wordorder.is_reordering(
            "Tavaliselt enne valimisi muutuvad lehed poliitilisemaks, kirjutades neist.",
            "Tavaliselt muutuvad lehed enne valimisi poliitilisemaks, kirjutades, neist.")

    def test_but_the_same_punctuation_in_a_new_place_is_fine(self):
        """Only the multiset is compared. A fronted constituent takes its
        comma with it, and that is still purely a re-ordering."""
        assert wordorder.is_reordering(
            "Kui sajab, ma jään koju.", "Kui sajab, jään ma koju.")


class TestTheRuleIsOnlyClaimedWhereItCanBeRead:
    """Two rules are claimed because two can be read off morphology. Calling
    everything else `other` is what keeps the explanations honest."""

    def test_v2_is_recognised(self):
        rule, moved = wordorder.classify(
            "Oktoobris vihmased päevad vahelduvad.",
            "Oktoobris vahelduvad vihmased päevad.")
        assert rule == "v2" and moved == "vahelduvad"

    def test_a_split_negation_is_recognised(self):
        rule, _ = wordorder.classify("Ma ei kunagi tea seda.",
                                     "Ma ei tea kunagi seda.")
        assert rule == "negation"

    def test_a_stylistic_move_is_not_dressed_up_as_a_rule(self):
        rule, _ = wordorder.classify(
            "Praegu on talv ja minu esimene semester varsti lõpeb.",
            "Praegu on talv ja minu esimene semester lõpeb varsti.")
        assert rule == "other"

    def test_the_v2_explanation_does_not_overstate_it(self):
        """The explanation says "обычно", as EKK (SÜ 92) does: the finite verb is usually
        second.
        """
        why = wordorder.WHY["v2"]
        assert "обычно" in why
        assert "всегда" not in why

    def test_the_unruled_explanation_claims_only_what_it_can(self):
        why = wordorder.WHY["other"]
        assert "носитель" in why          # a native wrote it
        assert "ошибк" in why             # and says this is not about an error

    def test_every_explanation_is_in_russian(self):
        for why in wordorder.WHY.values():
            assert any("Ѐ" <= ch <= "ӿ" for ch in why)


class TestGenerationIsRefused:
    """The measurement that ruled it out, kept as a test so the reasoning is
    not quietly dropped by someone adding a corpus generator later."""

    def test_the_module_has_no_corpus_generator(self):
        assert not hasattr(wordorder, "from_corpus")

class TestThePracticeShape:
    @pytest.fixture
    def content(self, tmp_path, pairs, monkeypatch):
        from eesti import config

        path = tmp_path / "content.db"
        monkeypatch.setattr(config, "CONTENT_DB", str(path))
        raw = tmp_path / "grammar_et.json"
        raw.write_text(json.dumps(
            [{"original": w, "correct": r} for w, r in pairs]), encoding="utf-8")
        from eesti.sources import connect

        conn = connect(path)
        assert wordorder.ingest(conn, raw) == 2
        return conn

    def test_items_reach_the_content_store(self, content):
        got = wordorder.items(content, limit=10)
        assert len(got) == 2

    def test_the_rule_bearing_item_comes_first(self, content):
        """A session opens on the rules that teach something (v2, then negation)."""
        assert wordorder.generate(count=2, seed=1, content=content)[0].rule == "v2"

    def test_it_offers_exactly_two_whole_sentences(self, content):
        for item in wordorder.generate(count=2, seed=1, content=content):
            assert len(item.choices) == 2
            assert set(item.choices) == {item.answer, item.distractor}

    def test_the_right_answer_is_not_always_in_the_same_place(self, content):
        firsts = {wordorder.generate(count=1, seed=s, content=content)[0].choices[0]
                  for s in range(12)}
        assert len(firsts) > 1, "a fixed position is learnable without reading"

    def test_grading_is_the_same_comparison_every_item_uses(self, content):
        """That is what lets this reach mastery and the review queue through
        the existing path rather than needing a loop of its own."""
        item = wordorder.generate(count=1, seed=1, content=content)[0]
        assert item.check(item.answer)
        assert not item.check(item.distractor)

    def test_the_rule_ships_with_the_exercise(self, content):
        item = wordorder.generate(count=1, seed=1, content=content)[0]
        assert item.reference["ekk_section"] == "SÜ 91"

    def test_no_corpus_is_an_empty_list_not_a_crash(self):
        assert wordorder.generate(count=3, content=None, path=None) == []

    def test_the_topic_now_has_a_generator(self):
        """`sonajark` has practice items."""
        from eesti.curriculum import by_id

        assert by_id("sonajark").generator == "wordorder"

    def test_the_practice_loop_serves_it(self, content):
        from eesti.practice import items_for

        got = items_for("sonajark", count=2, seed=1)
        assert got and all(i.choices for i in got)


class TestTheLicenceDecisionIsRecorded:
    def test_the_source_is_registered_as_ungranted(self):
        from eesti.sources import REGISTRY

        src = next(s for s in REGISTRY if s.id == wordorder.SOURCE_ID)
        assert src.redistributable is False
        assert "no licence" in src.licence.lower()


class TestEveryFetchedPairFileIsRead:
    """The default input files are derived from the fetch table, so every fetched pair
    file (including `grammar2_et`) feeds the pool.
    """

    def test_the_default_covers_every_gec_pair_file_the_fetcher_knows(self):
        from eesti.evals.fetch import DATASETS

        names = {p.stem for p in wordorder.bench_files()}
        assert names == {n for n in DATASETS if n.startswith("grammar")}
        assert "grammar2_et" in names, "the overlooked file must be in the default"
        assert "grammar_et_train" in names, "and the split nothing ever fetched"


class TestTheTwoSplitsOfGrammarEt:
    """`grammar_et`'s test and train splits land in separate files."""

    def test_each_entry_names_its_own_file(self):
        """Keyed by filename, not by dataset. Keyed by dataset, the second
        `grammar_et` entry would overwrite the first — silently, and in the
        direction that empties the eval track."""
        from eesti.evals.fetch import DATASETS

        assert len({k for k in DATASETS}) == len(DATASETS)
        datasets = [d for d, _, _ in DATASETS.values()]
        assert datasets.count("grammar_et") == 2, "both splits are fetched"

    def test_the_eval_track_still_reads_the_test_split(self):
        """Its score is compared across runs. Repointing this file at eight
        times the rows would move a number that is supposed to mean one thing."""
        from eesti.evals.external import DATASET
        from eesti.evals.fetch import DATASETS

        assert DATASET.name == "grammar_et.json"
        assert DATASETS["grammar_et"] == ("grammar_et", "test", 1000)

    def test_the_train_split_is_a_separate_file(self):
        from eesti.evals.fetch import DATASETS

        name, split, rows = DATASETS["grammar_et_train"]
        assert (name, split) == ("grammar_et", "train")
        assert rows > 1000, "the point of it"

    def test_fetch_writes_under_the_key_not_the_dataset(self, tmp_path, monkeypatch):
        import json

        from eesti.evals import fetch as fetch_mod

        class _Resp:
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def read(self): return json.dumps({"rows": []}).encode()

        monkeypatch.setattr(fetch_mod.urllib.request, "urlopen",
                            lambda *a, **k: _Resp())
        out = fetch_mod.fetch("grammar_et", "train", 10, tmp_path,
                              key="grammar_et_train")
        assert out.name == "grammar_et_train.json"
        assert not (tmp_path / "grammar_et.json").exists(), (
            "or the train fetch lands on the eval track's file")

    def test_it_looks_where_fetch_bench_writes(self, tmp_path):
        assert all(p.parent == tmp_path for p in wordorder.bench_files(tmp_path))

    def test_absence_is_not_an_error(self, tmp_path):
        """A fresh checkout has none of these: ungranted data, git-ignored."""
        assert all(wordorder.load(p) == [] for p in wordorder.bench_files(tmp_path))

    def test_two_files_merge_rather_than_collide(self, tmp_path, pairs, monkeypatch):
        """Item ids are content hashes, so the same pair in both files is one
        item and a different pair is two."""
        from eesti.sources import connect

        first = tmp_path / "grammar_et.json"
        second = tmp_path / "grammar2_et.json"
        first.write_text(json.dumps(
            [{"original": pairs[0][0], "correct": pairs[0][1]}]), encoding="utf-8")
        second.write_text(json.dumps(
            [{"original": pairs[0][0], "correct": pairs[0][1]},
             {"original": pairs[1][0], "correct": pairs[1][1]}]), encoding="utf-8")

        conn = connect(tmp_path / "content.db")
        wordorder.ingest(conn, first)
        wordorder.ingest(conn, second)
        assert len(wordorder.items(conn, limit=10)) == 2
