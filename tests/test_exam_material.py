"""HARNO's own task material, read inside the app.

The exam board publishes its past tasks for candidates to practise with, and
this learner keeps a private copy (`cli harvest-exam --download`). What these
tests guard is the learner-visible half: a downloaded task opens in the app,
a task that was not downloaded says so instead of failing silently, and no
request can walk out of the exam folder.
"""

from __future__ import annotations

import json

import pytest

pytest.importorskip("httpx2", reason="TestClient needs the httpx2 transport")

from eesti import config  # noqa: E402
from eesti.sources import Item, add_items, connect, register  # noqa: E402


@pytest.fixture
def material(tmp_path, monkeypatch):
    """A content database holding one downloaded task and one link-only task."""
    db = str(tmp_path / "content.db")
    conn = connect(db)
    register(conn)
    here = Item(source_id="harno", skill="lugemine", level="B1",
                title="B1 Lu1 kuulutus", body="Esimene ülesanne. Küsimused 1-9.",
                meta={"url": "https://harno.ee/x/B1_Lu1.pdf", "kind": "ulesanne",
                      "format": "pdf", "file": "B1/B1_Lu1.pdf", "external": False})
    away = Item(source_id="harno", skill="kuulamine", level="B1",
                title="B1 kuulamisülesanne nr 1", body="",
                audio_url="https://projektid.edu.ee/x/B1.mp3",
                meta={"url": "https://projektid.edu.ee/x/B1.mp3", "kind": "ulesanne",
                      "format": "mp3", "file": None, "external": True})
    add_items(conn, [here, away])
    conn.close()
    monkeypatch.setattr(config, "CONTENT_DB", db)

    pdf = tmp_path / "exam" / "B1" / "B1_Lu1.pdf"
    pdf.parent.mkdir(parents=True)
    pdf.write_bytes(b"%PDF-1.4\n%%EOF\n")
    return {"here": here.id, "away": away.id}


def test_a_downloaded_task_opens_in_the_app(client, material):
    r = client.get(f"/api/exam/file/{material['here']}")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/pdf")


def test_its_text_is_readable_with_the_exam_board_named(client, material):
    r = client.get(f"/api/exam/text/{material['here']}")
    assert r.status_code == 200
    body = r.json()
    assert "Esimene ülesanne" in body["text"]
    assert "Noorteamet" in body["note"]


def test_a_task_that_was_not_downloaded_says_so(client, material):
    """Rather than a blank reader: the learner is told to open the link."""
    for route in ("file", "text"):
        r = client.get(f"/api/exam/{route}/{material['away']}")
        assert r.status_code == 404
        assert "ссылк" in r.json()["detail"] or "файл" in r.json()["detail"]


def test_a_meta_row_pointing_out_of_the_folder_is_refused(client, material, tmp_path):
    """The path is data in a database, so it is checked rather than trusted."""
    secret = tmp_path / "secret.pdf"
    secret.write_bytes(b"%PDF-1.4\n")
    conn = connect(config.CONTENT_DB)
    with conn:
        conn.execute("UPDATE items SET meta = ? WHERE id = ?",
                     (json.dumps({"file": "../secret.pdf"}), material["here"]))
    conn.close()
    assert client.get(f"/api/exam/file/{material['here']}").status_code == 404


def test_an_unknown_item_is_not_found(client, material):
    assert client.get("/api/exam/file/nope").status_code == 404
    assert client.get("/api/exam/text/nope").status_code == 404
