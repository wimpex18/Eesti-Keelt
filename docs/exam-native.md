# Native official exam material

The original HARNO PDF and page image remain available in the app. Private
JSON sidecars add text and figures by page, the extraction method, sparse-page
flags and candidate questions. Figure positions come from the PDF layout so
image-heavy pages stay in reading order. In Cloud Shell, after pulling the
current `main` branch:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --quiet pypdf pypdfium2 pdfplumber Pillow
sudo apt-get update
sudo apt-get install -y tesseract-ocr tesseract-ocr-est tesseract-ocr-eng
.venv/bin/python -m eesti.cli prepare-exam --root data/exam --ocr
bash deploy/push-exam.sh
```

On a machine without Tesseract, omit `--ocr` and the two `apt-get` lines.

The source and sidecar are owner-only under `data/exam/`, not in Git. The API
rejects a sidecar whose PDF hash changed. A candidate is **not** graded until
the PDF and parsed questions are visually checked and their hashes are added
to `eesti/exam_native.py`. The checked A2 first reading task has six A/B/C
questions and a printed key on page 2. The checked B1 first reading task has
nine situations, six separate image ads and a printed key on page 3. Grading
them is practice only: it never changes FSRS, mastery or readiness. Other
layouts stay ungraded; no model
guesses an answer. Sparse pages show the original page and an extraction note.

The current 29 A2/B1 task PDFs yielded two verified exercise types. Sparse and
OCR pages need visual review: individual image OCR preserves figure boundaries
but still misreads some letters and digits.
This parser intentionally has narrow coverage; the next task type needs its
own extractor and visual check. For layout-heavy or
scanned source files, [Docling](https://github.com/docling-project/docling)
offers a free local structured-document pipeline, while
[pdfplumber](https://github.com/jsvine/pdfplumber) provides the image
coordinates used here. The
[PaddleOCR PP-OCRv5](https://paddlepaddle.github.io/PaddleOCR/latest/en/version3.x/algorithm/PP-OCRv5/PP-OCRv5_multi_languages.html)
supports Estonian. Neither supplies a trustworthy answer key. The offline
Tesseract path is the small OCR option here; it does not add a model to Cloud
Run. Review its text against the original before making new graded controls.
