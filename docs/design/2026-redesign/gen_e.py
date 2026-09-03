# -*- coding: utf-8 -*-
"""Write every artboard file and the canvas manifest."""
import json, io, os
from gen_a import artboard
from gen_b import D
from gen_c import D2
from gen_d import M

D.update(D2)

DESK = [
    ("Main",       "Desktop · Rada",        "path", 1290),
    ("Harjutused", "Desktop · Harjutused",  "drill", 890),
    ("Lugemine",   "Desktop · Lugemine",    "read", 880),
    ("Sonavara",   "Desktop · Sõnavara",    "sonad", 880),
    ("Kuulamine",  "Desktop · Kuulamine",   "listen", 1310),
    ("Raakimine",  "Desktop · Rääkimine",   "speak", 1150),
    ("Kirjutamine","Desktop · Kirjutamine", "write",   1230),
    ("Jarjekord",  "Desktop · Järjekord",   "review", 1000),
    ("Toovihikud", "Desktop · Töövihikud",  "vihikud", 880),
    ("Ulevaade",   "Desktop · Ülevaade",    "exam", 1230),
    ("Edenemine",  "Desktop · Edenemine",   "status", 1420),
]
MOB = [
    ("MobiilRada",        "Mobiil · Rada",        "path"),
    ("MobiilHarjutused",  "Mobiil · Harjutused",  "drill"),
    ("MobiilLugemine",    "Mobiil · Lugemine",    "read"),
    ("MobiilSonavara",    "Mobiil · Sõnavara",    "sonad"),
    ("MobiilKuulamine",   "Mobiil · Kuulamine",   "listen"),
    ("MobiilRaakimine",   "Mobiil · Rääkimine",   "speak"),
    ("MobiilKirjutamine", "Mobiil · Kirjutamine", "write"),
    ("MobiilJarjekord",   "Mobiil · Järjekord",   "review"),
    ("MobiilToovihikud",  "Mobiil · Töövihikud",  "vihikud"),
    ("MobiilUlevaade",    "Mobiil · Ülevaade",    "exam"),
    ("MobiilEdenemine",   "Mobiil · Edenemine",   "status"),
]

boards, files = [], {}

# Page 1 — desktop, rows of four.
COLW, GAPX, GAPY = 1440, 120, 180
rows = [DESK[0:4], DESK[4:8], DESK[8:11]]
y = 0
for row in rows:
    for i, (name, title, key, h) in enumerate(row):
        files[name + ".dc.html"] = artboard(D[key])
        boards.append({"file": name + ".dc.html", "title": title,
                       "x": i * (COLW + GAPX), "y": y, "w": COLW, "h": h,
                       "page": "page-1", "print": "fixed"})
    y += max(r[3] for r in row) + GAPY

# Page 2 — mobile, rows of six.
MW, MH, MGX, MGY = 390, 844, 90, 170
for i, (name, title, key) in enumerate(MOB):
    col, row = i % 6, i // 6
    files[name + ".dc.html"] = artboard(M[key])
    boards.append({"file": name + ".dc.html", "title": title,
                   "x": col * (MW + MGX), "y": row * (MH + MGY),
                   "w": MW, "h": MH, "page": "page-2", "print": "fixed"})

# Page 3 — foundations.
files["Alused.dc.html"] = artboard(D2["found"])
boards.append({"file": "Alused.dc.html", "title": "Alused · дизайн-система",
               "x": 0, "y": 0, "w": 1180, "h": 1540,
               "page": "page-3", "print": "flow"})

canvas = {
    "artboards": boards,
    "pages": [{"id": "page-1", "name": "Desktop"},
              {"id": "page-2", "name": "Mobiil"},
              {"id": "page-3", "name": "Alused"}],
    "annotations": [
        {"id": "nav-note", "x": 0, "y": -150, "w": 620, "page": "page-1",
         "text": "Навигация переехала в боковую панель: режим (Õppimine / "
                 "Kordamine / Eksam) — заголовок группы, раздел — строка под ним. "
                 "Семь вкладок в одну строку больше нигде не сжимаются."},
        {"id": "grid-note", "x": 700, "y": -150, "w": 620, "page": "page-1",
         "text": "1440 × сетка 248 / гибкая колонка / 300. Контент не шире 828 px, "
                 "правая колонка — то, что раньше пряталось за кликом."},
        {"id": "tab-note", "x": 0, "y": -150, "w": 660, "page": "page-2",
         "text": "Внизу три режима вместо семи вкладок — 44+ px на палец. Разделы "
                 "стали строкой чипов вверху. Карточка слова садится ровно на "
                 "панель (bottom: 84 px) и больше её не перекрывает."},
        {"id": "lang-note", "x": 760, "y": -150, "w": 600, "page": "page-2",
         "text": "Правило языка сохранено: эстонский — интерфейс и термины, "
                 "русский — всё, что объясняет и предупреждает."},
    ],
    "launch": {"view": "canvas", "page": "page-1"},
}
files["canvas.json"] = json.dumps(canvas, ensure_ascii=False, indent=2)

here = os.path.dirname(os.path.abspath(__file__))
for name, body in files.items():
    with io.open(os.path.join(here, name), "w", encoding="utf-8") as fh:
        fh.write(body)
print("wrote %d files" % len(files))
