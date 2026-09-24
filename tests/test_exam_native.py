"""Only a visually reviewed source and exact parse can be graded."""

from __future__ import annotations

import json
from types import SimpleNamespace

from eesti import exam_native


def test_numbered_questions_need_complete_options_and_printed_key():
    pages = [
        {"number": 1, "text": "1. Kas siin tohib oodata?  A Ei taha.\n"
                              "B Ei või.\nC Ei ole."},
        {"number": 2, "text": "VASTUSED\n1. B"},
    ]
    questions = exam_native._multiple_choice(pages)
    assert questions == [{"number": 1, "page": 1,
                          "prompt": "Kas siin tohib oodata?",
                          "options": {"A": "Ei taha.", "B": "Ei või.",
                                      "C": "Ei ole."}, "answer": "B"}]
    pages[1]["text"] = "VASTUSED\n1. D"
    assert exam_native._multiple_choice(pages) == []


def test_changed_source_or_parse_revokes_review(tmp_path, monkeypatch):
    source = tmp_path / "task.pdf"
    source.write_bytes(b"reviewed PDF")
    question = {"number": 1, "page": 1, "prompt": "Kuhu?",
                "options": {"A": "Siia", "B": "Sinna", "C": "Koju"},
                "answer": "C"}
    digest = exam_native._exercise_digest("multiple-choice", [question], [])
    monkeypatch.setattr(exam_native, "REVIEWED", {exam_native._sha(source): digest})
    data = {"version": exam_native.VERSION, "source_sha256": exam_native._sha(source),
            "pages": [], "kind": "multiple-choice", "figures": [],
            "questions": [question], "verified": False, "note": "HARNO"}
    exam_native.sidecar(source).write_text(json.dumps(data))
    assert exam_native.load(source)["verified"] is True
    data["questions"][0]["answer"] = "A"
    exam_native.sidecar(source).write_text(json.dumps(data))
    assert exam_native.load(source)["verified"] is False
    source.write_bytes(b"changed PDF")
    assert exam_native.load(source) is None


def test_figures_follow_page_position_not_pdf_resource_order():
    page = SimpleNamespace(images=[SimpleNamespace(name=name) for name in
                                   ("ImageC.jpg", "ImageA.jpg", "ImageB.jpg")])
    layout = SimpleNamespace(images=[
        {"name": "ImageC", "top": 100, "x0": 300},
        {"name": "ImageA", "top": 100, "x0": 20},
        {"name": "ImageB", "top": 100, "x0": 160},
    ])
    assert [x["index"] for x in exam_native._images(page, layout)] == [2, 3, 1]


def test_matching_requires_nine_prompts_six_figures_and_printed_key():
    pages = [
        {"number": 1, "text": "Situatsioonid 1–9\n" + "\n".join(
            f"{n}. Olukord {n}" for n in range(1, 10)), "images": []},
        {"number": 2, "text": "Kuulutused A–F", "images": [
            {"index": n} for n in range(1, 7)]},
        {"number": 3, "text": "Lugemistesti vastused\n" + "\n".join(
            f"{n}. {chr(65 + (n - 1) % 6)}" for n in range(1, 10)),
         "images": []},
    ]
    questions, figures = exam_native._matching(pages)
    assert len(questions) == 9
    assert questions[0]["answer"] == "A"
    assert [f["letter"] for f in figures] == list("ABCDEF")
    pages[2]["text"] = "Lugemistesti vastused\n1. A"
    assert exam_native._matching(pages) == ([], [])
