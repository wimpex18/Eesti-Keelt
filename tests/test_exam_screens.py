"""Exam screens a learner was misled by (DEV-53).

Found in the October 2026 walkthrough: the only sitting offered had closed its
registration, with a countdown and no warning; EIS's interactive tasks were
labelled "в приложении" though they can only be solved on EIS; official files
were listed by raw file name; a mock showed "4 из 5" and nothing about which;
the owner's Notion queue showed to every learner.
"""

from __future__ import annotations

from datetime import date

import pytest

pytest.importorskip("httpx2", reason="TestClient needs the httpx2 transport")

from eesti import config, exam, library  # noqa: E402
from eesti.sources import Item, add_items, connect, register  # noqa: E402

GUEST = {"x-eesti-scope": "guest", "x-eesti-guest": "exam-screens"}


class TestASittingWhoseRegistrationClosed:
    sitting = exam.Session("B1", date(2026, 11, 8), date(2026, 10, 1))

    def test_it_says_registration_is_closed(self):
        assert self.sitting.to_dict(today=date(2026, 10, 8))["registration_open"] is False
        assert self.sitting.to_dict(today=date(2026, 9, 30))["registration_open"] is True

    @staticmethod
    def _readiness(decide, sitting):
        from eesti.readiness import Readiness

        return Readiness(level="B1", parts={}, grammar={}, vocabulary={}, verdict="",
                         days_to_decide=decide, days_to_sitting=sitting,
                         target=(date(2026, 10, 1), date(2026, 11, 8)))

    def test_the_closing_day_is_still_open(self):
        r = self._readiness(0, 38)
        assert "закрыта" not in r.countdown and "закрыта" not in r.to_dict()["deadline"]["note"]
        assert self.sitting.to_dict(today=date(2026, 10, 1))["registration_open"] is True

    def test_a_past_sitting_is_not_offered_as_still_possible(self):
        assert "можно" not in self._readiness(-60, -3).to_dict()["deadline"]["note"]

    def test_the_countdown_says_so_beside_the_days_left(self):
        from eesti.readiness import Readiness

        r = Readiness(level="B1", parts={}, grammar={}, vocabulary={}, verdict="",
                      days_to_decide=-7, days_to_sitting=31,
                      target=(date(2026, 10, 1), date(2026, 11, 8)))
        assert "регистрация закрыта" in r.countdown
        assert "закрыта" in r.to_dict()["deadline"]["note"]


@pytest.fixture
def official(tmp_path, monkeypatch):
    db = str(tmp_path / "content.db")
    conn = connect(db)
    register(conn)
    eis = Item(source_id="eis", skill="lugemine", level="B1",
               title="Lugemine 1 (B1-tase, harjutusülesanne)",
               body="Loe kuulutusi (A – F). 1. Nädalavahetusel … -- Vali -- A B C D E F",
               meta={"url": "https://eis.ekk.edu.ee/x", "kind": "ulesanne"})
    harno = Item(source_id="harno", skill="lugemine", level="B1",
                 title="B1 Lu2Avariant-1 2", body="Teine ülesanne.",
                 meta={"url": "https://harno.ee/x/B1_Lu2Avariant-1_2.pdf",
                       "kind": "ulesanne", "format": "pdf"})
    named = Item(source_id="harno", skill="kirjutamine", level="B1", title="teade",
                 body="Kirjuta teade.",
                 meta={"url": "https://harno.ee/x/teade.pdf", "kind": "ulesanne",
                       "format": "pdf"})
    add_items(conn, [eis, harno, named])
    conn.close()
    monkeypatch.setattr(config, "CONTENT_DB", db)
    tasks = [t for part in library.exam_material(connect(db), "B1")["ulesanded"].values()
             for t in part]
    return {t["id"]: t for t in tasks}, eis.id, harno.id, named.id


class TestOfficialTasks:
    def test_an_eis_task_says_it_is_solved_on_eis(self, official):
        tasks, eis, harno, _ = official
        assert tasks[eis]["solved_on"] == "eis"
        assert tasks[harno]["solved_on"] is None

    def test_a_file_name_title_gets_a_readable_label(self, official):
        tasks, _, harno, named = official
        assert tasks[harno]["label"] == "Lugemine · ülesanne 2"
        assert tasks[named]["label"] == "teade"   # already a name, kept

    @pytest.mark.parametrize("title, skill, label", [
        ("A2 Lugemine Neljas ülesanne2", "lugemine", "Lugemine · ülesanne 4"),
        ("A2 Rääkimine Teine ülesamnne", "raakimine", "Rääkimine · ülesanne 2"),
        ("B1 Ku3 yl lünkülesanne", "kuulamine", "Kuulamine · ülesanne 3"),
        ("Lugemine 1 (B1-tase, harjutusülesanne)", "lugemine",
         "Lugemine 1 (B1-tase, harjutusülesanne)"),
        ("B1 kuulamisülesanne nr 1", "kuulamine", "B1 kuulamisülesanne nr 1"),
    ])
    def test_harnos_file_name_shapes(self, title, skill, label):
        assert library.task_label(title, skill) == label


class TestMockReview:
    def test_reading_returns_each_item_with_its_solution(self, client):
        section = client.get("/api/mock/A2/lugemine?seed=5").json()
        answers = [{"token": t["token"], "given": "vale"} for t in section["tasks"]]
        got = client.post("/api/mock/A2/lugemine",
                          json={"seconds": 60, "answers": answers}).json()
        assert len(got["items"]) == len(answers)
        assert all(not row["correct"] and row["solution"] and "____" not in row["solution"]
                   for row in got["items"])

    def test_listening_returns_each_sentence_and_what_was_typed(self, client):
        section = client.get("/api/mock/A2/kuulamine?seed=2").json()
        answers = [{"text": t["text"], "given": ""} for t in section["tasks"]]
        got = client.post("/api/mock/A2/kuulamine",
                          json={"seconds": 60, "answers": answers}).json()
        assert [row["text"] for row in got["items"]] == [t["text"] for t in section["tasks"]]


class TestTheErrorLogIsTheOwners:
    ROW = {"wrong": "ma elab", "correct": "ma elan", "why": "", "tag": "verb-form"}

    def test_a_guest_sees_no_queue(self, client):
        got = client.get("/api/notion/pending", headers=GUEST).json()
        assert got["owner"] is False and got["items"] == []

    def test_a_guest_cannot_queue(self, client):
        assert client.post("/api/notion/queue", json=self.ROW, headers=GUEST).status_code == 403

    def test_the_owner_still_can(self, client):
        assert client.post("/api/notion/queue", json=self.ROW).status_code == 200
        got = client.get("/api/notion/pending").json()
        assert got["owner"] is True and got["items"]
