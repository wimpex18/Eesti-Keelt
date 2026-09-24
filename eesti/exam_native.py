"""Private, page-aware extraction of HARNO PDFs for the in-app exam reader.

Extraction is a draft, not an answer key. Only a source and parsed result that
were checked against the original PDF may expose graded questions. Sidecars
live beside the owner-only PDFs and are never committed to Git.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import pdfplumber
from pypdf import PdfReader

VERSION = 2
MIN_TEXT = 50

# These PDFs and parsed exercises were checked visually against their original
# pages on 2026-09-24. A changed file OR parser result drops back to ungraded.
REVIEWED: dict[str, str] = {
    "127d16334a101fc57c4a1c50512c76d3b9b2d3f30636f4751c3ee89b3d238b23":
        "8763b5f0c4c6094d42925550a26c37e11ec7e7b6ed5215709b3e748a377f23db",
    "0897192b62c1852bf33ecb41f005a42ab2a001f408bd8ba693934b4235d7e25d":
        "8f853f0bf1b1aa0628d992790969aa82df3448ead9d468a8f9ab9b492eb4475b",
}


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _ocr_page(path: Path, number: int) -> str:
    """Optional offline Estonian OCR. Never run in a learner request."""
    if not shutil.which("tesseract"):
        raise RuntimeError("tesseract is not installed")
    import pypdfium2 as pdfium

    with tempfile.TemporaryDirectory() as tmp:
        image = Path(tmp) / "page.png"
        doc = pdfium.PdfDocument(path)
        try:
            page = doc[number - 1]
            try:
                bitmap = page.render(scale=2.5)
                try:
                    bitmap.to_pil().save(image)
                finally:
                    bitmap.close()
            finally:
                page.close()
        finally:
            doc.close()
        done = subprocess.run(
            ["tesseract", str(image), "stdout", "-l", "est+eng"],
            capture_output=True, text=True, timeout=120, check=False,
        )
        if done.returncode:
            raise RuntimeError(done.stderr.strip() or "tesseract failed")
        return done.stdout.strip()


def _ocr_image(data: bytes, suffix: str) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        image = Path(tmp) / f"image{suffix}"
        image.write_bytes(data)
        done = subprocess.run(
            ["tesseract", str(image), "stdout", "-l", "est+eng"],
            capture_output=True, text=True, timeout=120, check=False,
        )
        if done.returncode:
            raise RuntimeError(done.stderr.strip() or "tesseract failed")
        return done.stdout.strip()


def _images(page, layout_page) -> list[dict]:
    """Embedded figures in visual reading order, with stable extraction index.

    PDF resource order is not page order: the B1 ad sheet stores C,A,B,F,D,E.
    pdfplumber gives each placed image its page coordinates and resource name.
    """
    placed: dict[str, list[dict]] = {}
    for image in layout_page.images:
        placed.setdefault(image["name"], []).append(image)
    found = []
    for index, image in enumerate(page.images, 1):
        name = Path(image.name).stem
        locations = placed.get(name) or []
        position = locations.pop(0) if locations else None
        found.append({"index": index, "name": image.name,
                      "top": position["top"] if position else float("inf"),
                      "left": position["x0"] if position else float("inf")})
    found.sort(key=lambda x: (round(x["top"] / 25), x["left"], x["top"]))
    return [{"index": x["index"], "name": x["name"]} for x in found]


def _multiple_choice(pages: list[dict]) -> list[dict]:
    """Recognise only the simple numbered A/B/C layout with a printed key.

    Anything ambiguous stays a page in the reader. No answer is inferred from
    the question text, a model, or a marked example.
    """
    key: dict[int, str] = {}
    for page in pages:
        text = page["text"]
        if not re.search(r"(?im)^\s*VASTUSED\s*$", text):
            continue
        for n, letter in re.findall(r"(?m)^\s*(\d+)\.\s*([ABC])\s*$", text):
            if int(n) in key:
                return []
            key[int(n)] = letter
    if not key:
        return []

    questions: list[dict] = []
    for page in pages:
        if re.search(r"(?im)^\s*VASTUSED\s*$", page["text"]):
            continue
        lines = page["text"].splitlines()
        current: dict | None = None
        for line in lines:
            match = re.match(r"^\s*([1-9]\d*)\.\s+(.+)", line)
            if match:
                if current:
                    questions.append(current)
                prompt = match.group(2).strip()
                # HARNO sometimes puts option A in a second column on the
                # same extracted line as the prompt.
                split = re.split(r"\s{2,}A\s+", prompt, maxsplit=1)
                current = {"number": int(match.group(1)), "page": page["number"],
                           "prompt": split[0].strip(), "options": {}}
                if len(split) == 2:
                    current["options"]["A"] = split[1].strip()
                continue
            if current:
                option = re.match(r"^\s*([ABC])\s+(.+?)\s*$", line)
                if option:
                    current["options"][option.group(1)] = option.group(2).strip()
        if current:
            questions.append(current)
    numbers = [q["number"] for q in questions]
    if (not numbers or numbers != list(range(1, len(numbers) + 1))
            or set(numbers) != set(key)
            or any(set(q["options"]) != {"A", "B", "C"} or not q["prompt"]
                   or any(not v for v in q["options"].values()) for q in questions)):
        return []
    for q in questions:
        q["answer"] = key[q["number"]]
    return questions


def _matching(pages: list[dict]) -> tuple[list[dict], list[dict]]:
    """Numbered situations matched to six printed A-F figure panels and key."""
    prompt_page = next((p for p in pages if re.search(
        r"Situatsioonid\s+1[–-]9", p["text"], re.I)), None)
    figure_page = next((p for p in pages if len(p["images"]) == 6 and re.search(
        r"Kuulutused\s+A[–-]F", p["text"], re.I)), None)
    answer_page = next((p for p in pages if re.search(
        r"Lugemistesti vastused", p["text"], re.I)), None)
    if not prompt_page or not figure_page or not answer_page:
        return [], []
    key = {int(n): letter for n, letter in re.findall(
        r"(?m)^\s*(\d+)\.\s*([A-F])\s*$", answer_page["text"])}
    if set(key) != set(range(1, 10)):
        return [], []
    questions = []
    for line in prompt_page["text"].splitlines():
        match = re.match(r"^\s*([1-9])\.\s+(.+)", line)
        if match:
            questions.append({"number": int(match.group(1)),
                              "page": prompt_page["number"],
                              "prompt": match.group(2).strip(),
                              "answer": key[int(match.group(1))]})
        elif questions and line.strip() and len(questions) < 9:
            # Wrapped situation text, if a future layout uses two lines.
            questions[-1]["prompt"] += " " + line.strip()
    if ([q["number"] for q in questions] != list(range(1, 10))
            or any(not q["prompt"] for q in questions)):
        return [], []
    figures = [{"letter": chr(65 + i), "page": figure_page["number"],
                "index": image["index"]}
               for i, image in enumerate(figure_page["images"])]
    return questions, figures


def _exercise_digest(kind: str, questions: list[dict], figures: list[dict]) -> str:
    body = json.dumps({"kind": kind, "questions": questions, "figures": figures},
                      ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"))
    return hashlib.sha256(body.encode()).hexdigest()


def extract(path: Path | str, *, ocr: bool = False) -> dict:
    """Create an owner-only draft with page text, OCR gaps, and safe candidates."""
    path = Path(path)
    pages = []
    reader = PdfReader(str(path))
    with pdfplumber.open(path) as layout:
        for number, (page, layout_page) in enumerate(
                zip(reader.pages, layout.pages, strict=True), 1):
            text = (page.extract_text() or "").strip()
            images = _images(page, layout_page)
            method = "pdf-text"
            # A short printed key is already machine-readable. OCR can garble
            # letter/number pairs, so keep the PDF text when a key is present.
            if len(text) < MIN_TEXT and ocr and not re.search(
                    r"(?im)^\s*VASTUSED\s*$", text):
                snippets = []
                for figure in images:
                    image = page.images[figure["index"] - 1]
                    try:
                        found = _ocr_image(image.data, Path(image.name).suffix)
                    except RuntimeError:
                        found = ""
                    if found:
                        snippets.append(f"Pilt {len(snippets) + 1}\n{found}")
                if snippets:
                    found = "\n\n".join(snippets)
                    method = "tesseract-est+eng-images"
                else:
                    try:
                        found = _ocr_page(path, number)
                    except RuntimeError:
                        found = ""
                    if found:
                        method = "tesseract-est+eng-page"
                if len(found) > len(text):
                    text = f"{text}\n\n{found}" if text else found
                else:
                    method = "pdf-text"
            pages.append({"number": number, "text": text, "method": method,
                          "images": images,
                          # OCR can mix words and digits even when long.
                          "needs_review": len(text) < MIN_TEXT or method != "pdf-text"})
    questions = _multiple_choice(pages)
    kind = "multiple-choice" if questions else "none"
    figures: list[dict] = []
    if not questions:
        questions, figures = _matching(pages)
        if questions:
            kind = "matching"
    sha = _sha(path)
    verified = bool(questions and REVIEWED.get(sha)
                    and REVIEWED[sha] == _exercise_digest(kind, questions, figures))
    return {"version": VERSION, "source_sha256": sha, "pages": pages,
            "kind": kind, "questions": questions, "figures": figures,
            "verified": verified,
            "note": "© Haridus- ja Noorteamet"}


def sidecar(path: Path | str) -> Path:
    return Path(path).with_suffix(".native.json")


def prepare(path: Path | str, *, ocr: bool = False) -> dict:
    path = Path(path)
    draft = extract(path, ocr=ocr)
    sidecar(path).write_text(json.dumps(draft, ensure_ascii=False, indent=2),
                             encoding="utf-8")
    return draft


def load(path: Path | str) -> dict | None:
    """Only use a sidecar for its exact PDF; re-check curated result on load."""
    path = Path(path)
    try:
        data = json.loads(sidecar(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if data.get("version") != VERSION or data.get("source_sha256") != _sha(path):
        return None
    questions = data.get("questions") or []
    data["verified"] = bool(questions and REVIEWED.get(data["source_sha256"])
                            and REVIEWED[data["source_sha256"]]
                            == _exercise_digest(data.get("kind", "none"), questions,
                                                data.get("figures") or []))
    return data
