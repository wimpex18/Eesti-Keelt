"""The blind check, the checked files and the build into content.db (ADR-0009, steps 3–4).

The Message Batches API is replaced by `FakeBatches`, which answers each request
with what a test tells it to: no test reaches Anthropic.
"""

from __future__ import annotations

import json
import re
import sqlite3
from types import SimpleNamespace

import pytest

from test_material import FIXTURE, draft, material, words  # noqa: F401  (fixture)


class FakeBatches:
    """`client.messages.batches`, answering from `reply(custom_id, prompt)`."""

    def __init__(self, reply):
        self.reply = reply
        self.created: list[list[dict]] = []
        self.polls = 0

    def create(self, requests):
        self.created.append(requests)
        return SimpleNamespace(id=f"msgbatch_{len(self.created)}")

    def retrieve(self, batch_id):
        self.polls += 1
        status = "ended" if self.polls > 1 else "in_progress"
        return SimpleNamespace(processing_status=status,
                               request_counts=SimpleNamespace(processing=1))

    def results(self, batch_id):
        requests = self.created[int(batch_id.split("_")[1]) - 1]
        for r in reversed(requests):            # any order: keyed by id, never position
            prompt = r["params"]["messages"][0]["content"]
            got = self.reply(r["custom_id"], prompt)
            if got is None:
                yield SimpleNamespace(custom_id=r["custom_id"],
                                      result=SimpleNamespace(type="errored"))
                continue
            message = SimpleNamespace(
                stop_reason="end_turn",
                content=[SimpleNamespace(type="text", text=json.dumps({"answer": got}))])
            yield SimpleNamespace(custom_id=r["custom_id"],
                                  result=SimpleNamespace(type="succeeded", message=message))


def client_for(reply):
    batches = FakeBatches(reply)
    return SimpleNamespace(messages=SimpleNamespace(batches=batches)), batches


def honest(custom_id: str, prompt: str) -> str:
    """A reader who answers from the text and cannot guess without it."""
    m = material()
    item = custom_id.split("-")[1]
    if custom_id.endswith("-blind"):
        return "ei tea"
    for q in m.questions:
        if q.id == item:
            return q.answer
    return next(g.word for g in m.gaps if g.id == item)


# ---------------------------------------------------------------------------
# What is asked
# ---------------------------------------------------------------------------

class TestTheRequests:
    def test_two_asks_per_question_and_one_per_gap(self):
        from eesti.material import blind

        asks = blind.asks([material()])
        assert len(asks) == 2 * 4 + 1
        assert {a.mode for a in asks if a.kind == "gap"} == {"text"}

    def test_ids_meet_the_batches_api_pattern_and_are_distinct(self):
        from eesti.material import blind

        ids = [a.custom_id for a in blind.asks([material(), material()])]
        assert len(set(ids)) == len(ids)
        assert all(re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", i) for i in ids)

    def test_the_blind_ask_has_no_text_and_no_key(self):
        from eesti.material import blind

        m = material()
        for a in blind.asks([m]):
            assert "Juhan:" not in a.prompt if a.mode == "blind" else "Juhan:" in a.prompt
            if a.kind == "question":
                key = next(q.answer for q in m.questions if q.id == a.item)
                question = next(q.question for q in m.questions if q.id == a.item)
                if a.mode == "blind":
                    assert key not in a.prompt.replace(question, "")

    def test_a_gap_is_blanked_and_named(self):
        from eesti.material import blind

        gap = next(a for a in blind.asks([material()]) if a.kind == "gap")
        assert "Üks kohv ja kaks ___, palun." in gap.prompt
        assert "sai, osastav" in gap.prompt

    def test_the_request_is_haiku_with_a_schema_and_a_cached_prompt(self):
        from eesti.material import blind

        r = blind.requests(blind.asks([material()]))[0]
        params = r["params"]
        assert params["model"] == "claude-haiku-5-5"
        assert params["output_config"]["format"]["type"] == "json_schema"
        assert params["system"][0]["cache_control"] == {"type": "ephemeral"}
        # Haiku 5.5 refuses sampling parameters and a prefill.
        assert "temperature" not in params
        assert params["messages"][-1]["role"] == "user"


# ---------------------------------------------------------------------------
# What is dropped
# ---------------------------------------------------------------------------

class TestTheJudgement:
    def _judge(self, reply):
        from eesti.material import blind

        m = material()
        items = blind.asks([m])
        client, _ = client_for(reply)
        batch = blind.submit(client, items)
        answers = blind.collect(client, batch)
        [(kept, dropped)] = blind.judge([m], items, answers)
        return kept, {f.where: f.message for f in dropped}

    def test_an_honest_reader_keeps_everything(self):
        kept, dropped = self._judge(honest)
        assert not dropped and len(kept.questions) == 4 and len(kept.gaps) == 1

    def test_a_disagreeing_answer_drops_the_question(self):
        kept, dropped = self._judge(
            lambda cid, p: "üks kohv" if cid == "m0-q1-text" else honest(cid, p))
        assert list(dropped) == ["question q1"] and "the key is" in dropped["question q1"]
        assert "q1" not in [q.id for q in kept.questions]

    def test_an_answer_found_without_the_text_drops_it_as_guessable(self):
        kept, dropped = self._judge(
            lambda cid, p: "neli eurot" if cid == "m0-q2-blind" else honest(cid, p))
        assert "guessable" in dropped["question q2"]

    def test_a_right_answer_with_words_around_it_still_agrees(self):
        """Graded as a learner's answer is: the span and at most three more words."""
        kept, dropped = self._judge(
            lambda cid, p: "Juhan soovib kaks saia" if cid == "m0-q1-text" else honest(cid, p))
        assert not dropped

    def test_a_request_that_errored_drops_its_item(self):
        """Unconfirmed is unchecked."""
        kept, dropped = self._judge(
            lambda cid, p: None if cid == "m0-q3-text" else honest(cid, p))
        assert "no blind answer" in dropped["question q3"]

    def test_a_blind_request_that_errored_keeps_the_item(self):
        """Not guessing is what a blind run should do."""
        kept, dropped = self._judge(
            lambda cid, p: None if cid == "m0-q3-blind" else honest(cid, p))
        assert not dropped

    def test_another_word_in_the_gap_drops_it(self):
        kept, dropped = self._judge(
            lambda cid, p: "saiu" if cid == "m0-g1-text" else honest(cid, p))
        assert "gap g1" in dropped and not kept.gaps

    def test_a_refusal_is_no_answer(self):
        from eesti.material.blind import _answer

        refused = SimpleNamespace(stop_reason="refusal", content=[])
        assert _answer(refused) is None
        fenced = SimpleNamespace(stop_reason="end_turn", content=[SimpleNamespace(
            type="text", text='```json\n{"answer": "kaks saia"}\n```')])
        assert _answer(fenced) == "kaks saia"

    def test_waiting_stops_at_its_limit(self):
        from eesti.material import blind

        client, batches = client_for(honest)
        batches.retrieve = lambda _id: SimpleNamespace(
            processing_status="in_progress", request_counts=None)
        assert blind.wait(client, "msgbatch_1", poll=10, limit=20,
                          sleep=lambda s: None, say=lambda s: None) is False


# ---------------------------------------------------------------------------
# Checked files
# ---------------------------------------------------------------------------

class TestCheckedFiles:
    def test_an_unstamped_material_is_never_written(self, tmp_path):
        from eesti.material import store

        with pytest.raises(ValueError, match="no blind check"):
            store.write_checked(material(), tmp_path)

    def test_a_stamped_material_is_written_where_its_unit_and_slug_say(self, tmp_path):
        from eesti.material import store
        from eesti.material.schema import load

        path = store.write_checked(
            store.stamp(material(), engine="claude-haiku-5-5", batch="b1"), tmp_path)
        assert path == tmp_path / "checked" / "kohvik" / "tellimine.json"
        back = load(path)
        assert back.checks["sha8"] == back.sha8() and back.checks["blind"]["batch"] == "b1"
        assert "Üks kohv" in path.read_text(encoding="utf-8")   # Estonian, not \\u escapes

    def test_a_file_edited_after_its_stamp_is_refused(self, tmp_path):
        from eesti.material import store

        stamped = store.stamp(material(), engine="claude-haiku-5-5", batch="b1")
        edited = stamped.model_copy(update={"title": "Teine pealkiri"})
        assert store.stamped(edited) == "the content changed after its checks"


# ---------------------------------------------------------------------------
# The command, end to end
# ---------------------------------------------------------------------------

@pytest.fixture
def words_path(words, tmp_path):  # noqa: F811 - the fixture imported above
    return tmp_path / "words.db"


def run(argv):
    import contextlib
    import io

    from eesti import cli

    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
        code = cli.main(argv)
    return code, out.getvalue()


class TestTheCommand:
    def _blind(self, monkeypatch, tmp_path, words_path, reply, drafts=None):
        import anthropic

        client, batches = client_for(reply)
        monkeypatch.setattr(anthropic, "Anthropic", lambda *a, **k: client)
        monkeypatch.setattr("eesti.material.blind.POLL_SECONDS", 0)
        monkeypatch.setattr("time.sleep", lambda s: None)
        code, out = run(["material", "blind", *(drafts or [str(FIXTURE)]),
                         "--root", str(tmp_path / "material"),
                         "--words-db", str(words_path), "--wait", "60"])
        return code, out, batches

    def test_check_passes_the_fixture(self, words_path):
        code, out = run(["material", "check", str(FIXTURE), "--words-db", str(words_path)])
        assert code == 0 and "pass: 4 questions, 1 gaps kept" in out

    def test_check_fails_a_broken_draft(self, words_path, tmp_path):
        bad = tmp_path / "bad.json"
        bad.write_text(json.dumps(draft(off_list=[]), ensure_ascii=False), encoding="utf-8")
        code, out = run(["material", "check", str(bad), "--words-db", str(words_path)])
        assert code == 1 and "FAIL [level]" in out

    def test_schema_prints_the_json_schema(self):
        code, out = run(["material", "schema"])
        assert code == 0 and json.loads(out)["title"] == "Material"

    def test_blind_writes_a_stamped_checked_file(self, monkeypatch, tmp_path, words_path):
        code, out, batches = self._blind(monkeypatch, tmp_path, words_path, honest)
        assert code == 0, out
        written = tmp_path / "material" / "checked" / "kohvik" / "tellimine.json"
        doc = json.loads(written.read_text(encoding="utf-8"))
        assert doc["checks"]["blind"]["engine"] == "claude-haiku-5-5"
        assert doc["checks"]["blind"]["batch"] == "msgbatch_1"
        assert len(batches.created[0]) == 9

    def test_blind_drops_an_item_and_stores_only_the_rest(self, monkeypatch, tmp_path,
                                                          words_path):
        reply = lambda cid, p: "neli eurot" if cid == "m0-q2-blind" else honest(cid, p)  # noqa: E731
        code, out, _ = self._blind(monkeypatch, tmp_path, words_path, reply)
        doc = json.loads((tmp_path / "material" / "checked" / "kohvik" /
                          "tellimine.json").read_text(encoding="utf-8"))
        assert [q["id"] for q in doc["questions"]] == ["q1", "q3", "q4"]
        assert "neli eurot" not in [q["answer"] for q in doc["questions"]]
        assert "guessable" in out

    def test_blind_stores_nothing_when_too_few_items_survive(self, monkeypatch, tmp_path,
                                                             words_path):
        """A key is never stored without the gates, before or after the blind check."""
        code, out, _ = self._blind(monkeypatch, tmp_path, words_path,
                                   lambda cid, p: "midagi muud")
        assert code == 1
        assert not (tmp_path / "material" / "checked").exists()

    def test_blind_asks_nothing_about_a_draft_the_gates_refuse(self, monkeypatch, tmp_path,
                                                               words_path):
        bad = tmp_path / "bad.json"
        bad.write_text(json.dumps(draft(off_list=[]), ensure_ascii=False), encoding="utf-8")
        code, out, batches = self._blind(monkeypatch, tmp_path, words_path, honest,
                                         drafts=[str(bad)])
        assert code == 1 and not batches.created

    def test_blind_only_asks_about_items_the_gates_kept(self, monkeypatch, tmp_path,
                                                        words_path):
        doc = draft()
        doc["questions"].append({"id": "q9", "question": "Mida Juhan ei söö?",
                                 "answer": "kooki"})
        path = tmp_path / "draft.json"
        path.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
        _, _, batches = self._blind(monkeypatch, tmp_path, words_path, honest,
                                    drafts=[str(path)])
        assert not any("-q9-" in r["custom_id"] for r in batches.created[0])

    def test_build_puts_checked_files_into_content_db(self, monkeypatch, tmp_path,
                                                      words_path):
        self._blind(monkeypatch, tmp_path, words_path, honest)
        content = tmp_path / "content.db"
        code, out = run(["material", "build", "--root", str(tmp_path / "material"),
                         "--content-db", str(content), "--words-db", str(words_path)])
        assert code == 0, out
        conn = sqlite3.connect(content)
        (ident, source, skill, body, meta), = conn.execute(
            "SELECT id, source_id, skill, body, meta FROM items")
        assert re.fullmatch(r"mat:kohvik:tellimine@[0-9a-f]{8}", ident)
        assert (source, skill) == ("grove-material", "lugemine")
        assert body.startswith("Mari: Tere! Mida te soovite?")
        meta = json.loads(meta)
        assert meta["label"].startswith("написано моделью")
        assert meta["engine"] == "hand-written test fixture"
        assert "questions" not in meta and "answer" not in json.dumps(meta)
        assert conn.execute("SELECT redistributable FROM sources WHERE id = ?",
                            ("grove-material",)).fetchone() == (1,)

    def test_build_refuses_a_file_edited_after_its_checks(self, monkeypatch, tmp_path,
                                                          words_path):
        self._blind(monkeypatch, tmp_path, words_path, honest)
        path = tmp_path / "material" / "checked" / "kohvik" / "tellimine.json"
        doc = json.loads(path.read_text(encoding="utf-8"))
        doc["questions"][0]["answer"] = "üks kohv"
        path.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
        content = tmp_path / "content.db"
        code, out = run(["material", "build", "--root", str(tmp_path / "material"),
                         "--content-db", str(content), "--words-db", str(words_path)])
        assert code == 1 and "changed after its checks" in out
        assert sqlite3.connect(content).execute(
            "SELECT COUNT(*) FROM items WHERE source_id = 'grove-material'").fetchone() == (0,)

    def test_build_removes_material_whose_file_is_gone(self, monkeypatch, tmp_path,
                                                       words_path):
        self._blind(monkeypatch, tmp_path, words_path, honest)
        content = tmp_path / "content.db"
        args = ["material", "build", "--root", str(tmp_path / "material"),
                "--content-db", str(content), "--words-db", str(words_path)]
        run(args)
        (tmp_path / "material" / "checked" / "kohvik" / "tellimine.json").unlink()
        assert run(args)[0] == 0
        assert sqlite3.connect(content).execute(
            "SELECT COUNT(*) FROM material").fetchone() == (0,)


def test_the_repositorys_checked_files_all_build(words):  # noqa: F811
    """Every committed file still passes the gates and matches its stamp.

    Run against the real EKI list when it is built; with the fixture list, a
    committed file's lemmas may simply be missing, so only the stamp is checked.
    """
    from pathlib import Path

    from eesti.material import store
    from eesti.material.schema import load
    from eesti.wordlist import available

    real = Path("data/eesti.db")
    conn = sqlite3.connect(real) if available(real) else None
    for path in store.checked_files():
        m = load(path)
        assert path == store.path_for(m), path
        if conn is None:
            assert store.stamped(m) is None, path
        else:
            assert store.verify(m, conn) is None, path
