"""The model-drafted glosses: drafted from EKI's Russian, gated by code, kept only
when a second model, blind, names the word again.

Failures prevented: a gloss the back-translation contradicts reaching the
dictionary; a checker that was shown the answer; a word the drafting model
skipped disappearing without a record; a run that cannot say what it cost.
"""

from __future__ import annotations

import json
import re
import shutil
from types import SimpleNamespace

import pytest

from eesti import config, dictionary, dictionary_glosses as glosses, evs, wordlist


@pytest.fixture
def words(tmp_path, monkeypatch, fixture_data):
    path = tmp_path / "eesti.db"
    shutil.copy(fixture_data["words"], path)
    monkeypatch.setattr(config, "DB_PATH", path)
    conn = wordlist.connect(path)
    levels = tmp_path / "A1A2B1.txt"
    levels.write_text("LEMMA\tPOS\tSAGEDUS\tTASE\nraamat\tS\t1\tA1\nkohv\tS\t1\tA1\n"
                      "auto\tS\t1\tA1\naga\tJ\t1\tA1\naru saama\tV\t1\tA1\n", encoding="utf-8")
    wordlist.import_official_levels(conn, levels)
    evs.store(conn, [evs.Entry("raamat", "s", ("книга",)), evs.Entry("kohv", "s", ("кофе",)),
                     evs.Entry("aru saama", "v", ("понимать",))])
    monkeypatch.setattr(glosses, "wanted", lambda: ["auto"])
    yield conn
    conn.close()


class FakeBatches:
    """The Message Batches API, answering with the given functions."""

    def __init__(self, answer):
        self.answer = answer
        self.batches: dict[str, list[dict]] = {}

    def create(self, requests):
        batch = f"msgbatch_{len(self.batches)}"
        self.batches[batch] = requests
        return SimpleNamespace(id=batch)

    def retrieve(self, batch):
        return SimpleNamespace(processing_status="ended")

    def results(self, batch):
        for request in self.batches[batch]:
            params = request["params"]
            text = self.answer(params["model"], params["messages"][0]["content"])
            message = SimpleNamespace(
                content=[SimpleNamespace(type="text", text=json.dumps(text, ensure_ascii=False))],
                stop_reason="end_turn",
                usage=SimpleNamespace(input_tokens=1000, output_tokens=500,
                                      cache_creation_input_tokens=0, cache_read_input_tokens=0))
            yield SimpleNamespace(custom_id=request["custom_id"],
                                  result=SimpleNamespace(type="succeeded", message=message))


DRAFTS = {"raamat": {"en": ["book"], "uk": ["книжка"]},
          "kohv": {"en": ["coffee"], "uk": ["чёрный кофе"]}}   # Russian letters, first word: refused
#: The checker's Estonian, by the gloss it was shown.
BACK = {"book": ["raamat"], "книжка": ["raamat"], "coffee": ["tee"],
        "зуб; зубець": ["hammas"], "город; сад": ["aed"], "сад; город": ["aed"]}
#: The words the checker says are not standard Ukrainian, by the gloss.
FLAGGED = {"город; сад": ["город"], "сад; город": ["город"]}


def answer(model, text):
    if model == glosses.MODEL:
        found = re.findall(r"id: (w\d+)\nheadword: (\S+)", text)
        return {"words": [{"id": i, **DRAFTS[w]} for i, w in found if w in DRAFTS]}
    found = re.findall(r"id: (i\d+)\npart of speech: [^\n]*\n\w+: ([^\n]*)", text)
    if "Ukrainian:" in text:
        return {"items": [{"id": i, "et": BACK.get(g, ["midagi"]), "not_ukrainian": FLAGGED.get(g, [])}
                          for i, g in found]}
    return {"items": [{"id": i, "et": BACK.get(g, ["midagi"])} for i, g in found]}


def check(drafts):
    """The blind back-translation of `drafts` on the fake checker, judged by code."""
    client = SimpleNamespace(messages=SimpleNamespace(batches=FakeBatches(answer)))
    asks, groups = glosses.back_requests(drafts)
    batch = client.messages.batches.create(requests=asks).id
    texts, _ = glosses.collect(client, batch)
    return glosses.judge(texts, groups, batch)


def run(tmp_path, words):
    """The whole pipeline, as `cli dictionary glosses` runs it, on fakes."""
    client = SimpleNamespace(messages=SimpleNamespace(batches=FakeBatches(answer)))
    found = glosses.candidates(words, tmp_path)
    requests, groups = glosses.draft_requests(found)
    batch = client.messages.batches.create(requests=requests).id
    texts, usage = glosses.collect(client, batch)
    drafts, refused = glosses.gate_drafts(texts, groups, batch)
    asks, checks = glosses.back_requests(drafts)
    check = client.messages.batches.create(requests=asks).id
    back, _ = glosses.collect(client, check)
    kept, dropped = glosses.judge(back, checks, check)
    glosses.append(tmp_path / "glosses.jsonl", kept)
    glosses.append(tmp_path / "rejected.jsonl", refused + dropped)
    return client, asks, kept, refused + dropped, usage


class TestTheMainSenseStaysFirst:
    """Ukrainian shares many words with Russian (*зуб*, *сад*, *суп*): a word
    spelt as EKI's Russian is no reason to drop it, and a secondary sense must
    never stand alone as the word's meaning (*hammas* is not *зубець*)."""

    def test_a_cognate_main_sense_is_kept(self):
        groups = {"d0": [glosses.Word("hammas", "s", ("зуб", "зубец"))]}
        texts = {"d0": json.dumps({"words": [{"id": "w1", "en": ["tooth"], "uk": ["зуб", "зубець"]}]})}
        drafts, refused = glosses.gate_drafts(texts, groups)
        assert {d.lang: d.gloss for d in drafts}["uk"] == ["зуб", "зубець"] and not refused
        kept, dropped = check([d for d in drafts if d.lang == "uk"])
        assert kept[0]["gloss"] == ["зуб", "зубець"] and kept[0]["check_prompt"] == "s9-back-2"

    def test_a_draft_whose_first_word_the_checker_flags_is_refused_whole(self):
        draft = glosses.Draft("aed", "uk", ["город", "сад"], ["сад", "огород"], "s")
        kept, refused = check([draft])
        assert kept == []
        assert refused[0]["stage"] == "back" and "город" in refused[0]["why"]
        assert refused[0]["flagged"] == ["город"]

    def test_a_flagged_secondary_word_is_dropped_and_the_entry_stays(self):
        draft = glosses.Draft("aed", "uk", ["сад", "город"], ["сад", "огород"], "s")
        kept, refused = check([draft])
        assert refused == []
        assert kept[0]["gloss"] == ["сад"] and kept[0]["draft"] == ["сад", "город"]
        assert kept[0]["flagged"] == ["город"]
        assert dictionary.check_record(kept[0]) is None

    def test_a_first_word_in_russian_letters_refuses_the_draft(self):
        assert dictionary.gate("uk", ["сыр", "сир"]) == ([], "Russian letters: сыр")
        assert dictionary.gate("uk", ["сир", "сыр"]) == (["сир"], None)
        assert dictionary.gate("en", ["café", "cafe"])[0] == []
        assert dictionary.gate("en", ["cafe", "café"]) == (["cafe"], None)

    def test_the_import_refuses_a_gloss_whose_main_sense_was_dropped(self):
        record = {"lemma": "aed", "lang": "uk", "gloss": ["город"], "draft": ["сад", "город"],
                  "anchor": ["сад"], "pos": "s", "engine": glosses.MODEL, "prompt": "s9-gloss-1",
                  "checker": glosses.CHECKER, "check_prompt": "s9-back-2", "back": ["aed"],
                  "flagged": []}
        assert "main sense" in dictionary.check_record(record)


class TestWhichWords:
    def test_only_single_words_ekis_russian_translates(self, words, tmp_path):
        got = [w.lemma for w in glosses.candidates(words, tmp_path)]
        assert set(got) == {"raamat", "kohv"}, "auto has no EVS Russian; a phrase is not drafted"
        assert glosses.candidates(words, tmp_path)[0].russian == ("книга",)

    def test_a_word_already_kept_or_refused_is_not_drafted_again(self, words, tmp_path):
        run(tmp_path, words)
        assert glosses.candidates(words, tmp_path) == []


class TestThePipeline:
    def test_a_gloss_the_blind_checker_names_back_is_kept_with_its_evidence(self, words,
                                                                            tmp_path):
        _, _, kept, _, _ = run(tmp_path, words)
        book = next(r for r in kept if (r["lemma"], r["lang"]) == ("raamat", "en"))
        assert book["gloss"] == ["book"] and book["back"] == ["raamat"]
        assert (book["engine"], book["prompt"]) == (glosses.MODEL, glosses.DRAFT_PROMPT)
        assert (book["checker"], book["check_prompt"]) == (glosses.CHECKER, glosses.CHECK_PROMPT)
        assert book["anchor"] == ["книга"]
        assert dictionary.check_record(book) is None

    def test_a_gloss_the_checker_reads_as_another_word_is_refused(self, words, tmp_path):
        _, _, kept, refused, _ = run(tmp_path, words)
        assert ("kohv", "en") not in {(r["lemma"], r["lang"]) for r in kept}
        coffee = next(r for r in refused if (r["lemma"], r["lang"]) == ("kohv", "en"))
        assert coffee["stage"] == "back" and "tee" in coffee["why"]

    def test_a_russian_spelling_passed_off_as_ukrainian_never_reaches_the_checker(
            self, words, tmp_path):
        _, asks, _, refused, _ = run(tmp_path, words)
        assert not any("чёрный" in a["params"]["messages"][0]["content"] for a in asks)
        assert next(r for r in refused if (r["lemma"], r["lang"]) == ("kohv", "uk"))["stage"] == "gate"

    def test_the_checker_is_never_shown_the_word_or_its_russian(self, words, tmp_path):
        _, asks, _, _, _ = run(tmp_path, words)
        prompts = " ".join(a["params"]["messages"][0]["content"] for a in asks)
        assert "raamat" not in prompts and "книга" not in prompts
        assert all(a["params"]["model"] == glosses.CHECKER != glosses.MODEL for a in asks)

    def test_a_word_the_drafting_reply_leaves_out_is_recorded_as_refused(self, words,
                                                                         tmp_path, monkeypatch):
        monkeypatch.setitem(DRAFTS, "raamat", None)
        monkeypatch.setattr(glosses, "candidates", lambda *a, **k: [
            glosses.Word("raamat", "s", ("книга",))])
        found = glosses.candidates(words, tmp_path)
        requests, groups = glosses.draft_requests(found)
        texts = {requests[0]["custom_id"]: json.dumps({"words": []})}
        drafts, refused = glosses.gate_drafts(texts, groups)
        assert drafts == [] and {r["why"] for r in refused} == {"no draft came back"}

    def test_the_files_are_sorted_and_import_cleanly(self, words, tmp_path):
        run(tmp_path, words)
        lines = (tmp_path / "glosses.jsonl").read_text(encoding="utf-8").splitlines()
        keys = [(json.loads(l)["lemma"], json.loads(l)["lang"]) for l in lines]
        assert keys == sorted(keys)
        stats = dictionary.import_glosses(words, tmp_path / "glosses.jsonl")
        assert stats == {"stored": 2, "refused": 0}
        assert dictionary.model_glosses(words, "raamat")["uk"]["words"] == ["книжка"]

    def test_a_run_says_what_it_cost(self, words, tmp_path):
        _, _, _, _, usage = run(tmp_path, words)
        assert glosses.cost(glosses.MODEL, usage) == pytest.approx(
            (usage["input"] * 2.0 + usage["output"] * 10.0) / 1_000_000)

    def test_the_system_prompts_are_the_cached_prefix(self, words, tmp_path):
        requests, _ = glosses.draft_requests(glosses.candidates(words, tmp_path))
        system = requests[0]["params"]["system"][0]
        assert system["text"] == glosses.DRAFT_SYSTEM
        assert system["cache_control"] == {"type": "ephemeral"}
