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
    from pypdf import PdfWriter

    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    writer.add_blank_page(width=612, height=792)
    with pdf.open("wb") as output:
        writer.write(output)
    return {"here": here.id, "away": away.id}


def test_a_downloaded_task_opens_in_the_app(client, material):
    r = client.get(f"/api/exam/file/{material['here']}")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/pdf")
    assert r.headers["content-disposition"].startswith("inline;")


def test_its_pdf_pages_render_inside_the_app(client, material):
    item = material["here"]
    assert client.get(f"/api/exam/pages/{item}").json() == {"pages": 2}
    image = client.get(f"/api/exam/page/{item}/1")
    assert image.status_code == 200
    assert image.headers["content-type"] == "image/png"
    assert image.content.startswith(b"\x89PNG\r\n\x1a\n")
    assert client.get(f"/api/exam/page/{item}/3").status_code == 404
    assert client.get(f"/api/exam/image/{item}/1/1").status_code == 404


def test_an_older_catalogue_finds_a_later_mounted_harno_file(
        client, material):
    """Publishing the catalogue before the bucket must not hide mounted files."""
    conn = connect(config.CONTENT_DB)
    with conn:
        conn.execute("UPDATE items SET meta = json_remove(meta, '$.file') "
                     "WHERE id = ?", (material["here"],))
    conn.close()

    from eesti import library

    rows = library.exam_material(connect(config.CONTENT_DB), "B1")
    tasks = [t for part in rows["ulesanded"].values() for t in part]
    here = next(t for t in tasks if t["id"] == material["here"])
    assert here["file"] is True
    assert client.get(f"/api/exam/file/{material['here']}").status_code == 200


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
    assert client.get(f"/api/exam/pages/{material['here']}").status_code == 404
    assert client.get(f"/api/exam/page/{material['here']}/1").status_code == 404


def test_a_deployment_without_the_files_links_out(client, material, monkeypatch,
                                                  tmp_path):
    """The task text travels with the library; the files only where the bucket
    is mounted (`deploy/push-exam.sh`). Where they are absent the catalogue must
    say so instead of offering a file that 404s."""
    from eesti import library

    monkeypatch.setattr(config, "EXAM_DIR", str(tmp_path / "no-mount"))
    rows = library.exam_material(connect(config.CONTENT_DB), "B1")
    tasks = [t for part in rows["ulesanded"].values() for t in part]
    here = next(t for t in tasks if t["title"] == "B1 Lu1 kuulutus")
    assert here["file"] is False
    # The text is in the library, so the task still opens — just not the file.
    assert here["local"] is True
    assert client.get(f"/api/exam/file/{material['here']}").status_code == 404


def test_an_unknown_item_is_not_found(client, material):
    assert client.get("/api/exam/file/nope").status_code == 404
    assert client.get("/api/exam/text/nope").status_code == 404


def test_only_reviewed_native_questions_can_be_scored(client, material, monkeypatch):
    from pathlib import Path

    from eesti import exam_native

    pdf = Path(config.EXAM_DIR) / "B1/B1_Lu1.pdf"
    q = {"number": 1, "page": 1, "prompt": "Kuhu?",
         "options": {"A": "Siia", "B": "Sinna", "C": "Koju"}, "answer": "C"}
    sha = exam_native._sha(pdf)
    monkeypatch.setattr(exam_native, "REVIEWED",
                        {sha: exam_native._exercise_digest("multiple-choice", [q], [])})
    draft = {"version": exam_native.VERSION, "source_sha256": sha,
             "pages": [{"number": 1, "text": "Kuhu?", "method": "pdf-text",
                        "needs_review": False}],
             "kind": "multiple-choice", "figures": [],
             "questions": [q], "verified": True, "note": "HARNO"}
    exam_native.sidecar(pdf).write_text(json.dumps(draft))
    base = f"/api/exam/native/{material['here']}"
    public = client.get(base)
    assert public.status_code == 200
    assert public.json()["questions"][0]["options"]["C"] == "Koju"
    assert "answer" not in public.json()["questions"][0]
    checked = client.post(base + "/check", json={"answers": {"1": "C"}})
    assert checked.json()["correct"] == 1
    assert client.post(base + "/check", json={"answers": {}}).status_code == 422
    draft["questions"][0]["answer"] = "A"
    exam_native.sidecar(pdf).write_text(json.dumps(draft))
    assert client.get(base).json()["questions"] == []
    assert client.post(base + "/check", json={"answers": {"1": "A"}}).status_code == 404


def test_reviewed_matching_accepts_six_figure_letters(client, material, monkeypatch):
    from pathlib import Path

    from eesti import exam_native

    pdf = Path(config.EXAM_DIR) / "B1/B1_Lu1.pdf"
    question = {"number": 1, "page": 1, "prompt": "Kuhu?", "answer": "F"}
    figures = [{"letter": letter, "page": 1, "index": n}
               for n, letter in enumerate("ABCDEF", 1)]
    sha = exam_native._sha(pdf)
    monkeypatch.setattr(exam_native, "REVIEWED",
                        {sha: exam_native._exercise_digest("matching", [question], figures)})
    exam_native.sidecar(pdf).write_text(json.dumps({
        "version": exam_native.VERSION, "source_sha256": sha,
        "pages": [], "kind": "matching", "figures": figures,
        "questions": [question], "verified": True, "note": "HARNO",
    }))
    base = f"/api/exam/native/{material['here']}"
    assert client.get(base).json()["figures"][5]["letter"] == "F"
    assert client.post(base + "/check", json={"answers": {"1": "F"}}).json()["correct"] == 1
    assert client.post(base + "/check", json={"answers": {"1": "G"}}).status_code == 422
