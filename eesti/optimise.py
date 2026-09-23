"""Fitting FSRS to this learner's own review history.

FSRS ships parameters fitted on millions of reviews. A personal fit beats them
only once there is enough history to fit — `review.MIN_REVIEWS_TO_FIT` — and
below that it fits noise and schedules worse. So this refuses, out loud, rather
than producing a number that looks like an improvement.

Two deliberate boundaries:

- **It runs where the learner is, not on the deployment.** The optimiser needs
  torch, pandas and tqdm (`pip install "fsrs[optimizer]"`), which is a few
  hundred megabytes the Cloud Run image will not carry for a job run once a
  year.
- **The result is evidence, not a file.** The fitted parameters are recorded as
  a `fsrs-parameters` event, so they travel with the log, survive a cold start,
  and can be replayed or rolled back like anything else the learner did.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone


def review_logs(log: sqlite3.Connection) -> list:
    """Every recorded review, as FSRS `ReviewLog` objects.

    The evidence log *is* the review history: `review.grade` records the rating,
    who chose it and when, which is exactly what the optimiser reads.
    """
    from fsrs import Rating, ReviewLog

    ratings = {"again": Rating.Again, "hard": Rating.Hard,
               "good": Rating.Good, "easy": Rating.Easy}
    out = []
    for row in log.execute(
            "SELECT ts, payload FROM events WHERE type = 'review' ORDER BY seq"):
        payload = json.loads(row["payload"])
        rating = ratings.get(str(payload.get("rating", "")).lower())
        if rating is None or not payload.get("id"):
            continue
        at = datetime.fromisoformat(row["ts"])
        out.append(ReviewLog(
            card_id=int.from_bytes(hashlib.sha256(payload["id"].encode()).digest()[:8]) % (2 ** 62),
            rating=rating,
            review_datetime=at if at.tzinfo else at.replace(tzinfo=timezone.utc),
            review_duration=payload.get("latency_ms"),
        ))
    return out


def fit(log: sqlite3.Connection, *, force: bool = False) -> dict:
    """Fit the parameters and record them. Returns what happened, in Russian.

    `force` fits anyway below the threshold — for trying it out, never for
    scheduling by.
    """
    from . import evidence, review

    history = review_logs(log)
    if len(history) < review.MIN_REVIEWS_TO_FIT and not force:
        return {
            "fitted": False,
            "reviews": len(history),
            "needed": review.MIN_REVIEWS_TO_FIT,
            "why_ru": (f"Повторений пока {len(history)}, а для настройки нужно "
                       f"около {review.MIN_REVIEWS_TO_FIT}. До этого "
                       "стандартные параметры FSRS точнее личных."),
        }
    try:
        from fsrs import Optimizer
    except ImportError as exc:  # pragma: no cover - depends on the extra
        raise RuntimeError(
            'the optimiser needs its extra: pip install "fsrs[optimizer]"') from exc

    fitted = tuple(float(x) for x in Optimizer(history).compute_optimal_parameters())
    if len(history) < review.MIN_REVIEWS_TO_FIT:
        return {"fitted": True, "applied": False, "reviews": len(history),
                "parameters": list(fitted),
                "why_ru": "Пробный расчёт: истории мало, расписание не изменено."}
    evidence.record("fsrs-parameters", {
        "parameters": list(fitted),
        "reviews": len(history),
        "fitted_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        # Which build fitted them, so a suspicious schedule can be traced.
        "engine": "py-fsrs",
    })
    return {"fitted": True, "applied": True, "reviews": len(history), "parameters": list(fitted),
            "why_ru": (f"Параметры пересчитаны по {len(history)} повторениям. "
                       "Расписание следующих карточек уже по ним.")}
