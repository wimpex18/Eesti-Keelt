"""Small, evidence-based course milestones; derived, never stored as currency."""

from __future__ import annotations

import sqlite3

from .config import LEVELS


def for_level(progress: sqlite3.Connection, level: str) -> list[dict]:
    if level not in LEVELS:
        raise ValueError(level)
    from .checkpoint import passed_levels
    from .curriculum import TOPICS
    from .mock import counts
    from .progress import mastered

    topic_ids = {t.id for t in TOPICS if t.level == level and t.generator}
    attempts = 0
    if topic_ids:
        placeholders = ",".join("?" for _ in topic_ids)
        attempts = progress.execute(
            f"SELECT COUNT(*) FROM attempts WHERE topic IN ({placeholders})",
            sorted(topic_ids),
        ).fetchone()[0]
    mastered_count = len(mastered(progress) & topic_ids)
    parts = counts(progress, level)
    touched = sum(parts.get(part, 0) > 0 for part in
                  ("kirjutamine", "kuulamine", "lugemine", "raakimine"))
    values = (
        ("first-practice", "Esimene samm", "Первая записанная тренировка.",
         min(attempts, 1), 1),
        ("first-topic", "Esimene teema", "Первая освоенная тема.",
         min(mastered_count, 1), 1),
        ("checkpoint", "Kontrolltöö", "Контрольная уровня пройдена.",
         int(level in passed_levels(progress)), 1),
        ("four-parts", "Neli osa", "Есть практика по всем четырём частям экзамена.",
         touched, 4),
    )
    return [{"id": id_, "et": et, "ru": ru, "current": current,
             "target": target, "complete": current >= target}
            for id_, et, ru, current, target in values]
