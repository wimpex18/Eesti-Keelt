"""The Worker only acknowledges evidence after its durable copy catches up."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKER = (ROOT / "deploy" / "worker.ts").read_text(encoding="utf-8")
PATH_JS = (ROOT / "eesti" / "web" / "js" / "path.js").read_text(encoding="utf-8")
REVIEW_JS = (ROOT / "eesti" / "web" / "js" / "review.js").read_text(encoding="utf-8")


def _block(signature: str, source: str = WORKER) -> str:
    start = source.index(signature)
    opening = source.index("{", start)
    depth = 0
    for at in range(opening, len(source)):
        if source[at] == "{":
            depth += 1
        elif source[at] == "}":
            depth -= 1
            if depth == 0:
                return source[opening + 1:at]
    raise AssertionError(f"unterminated block: {signature}")


def test_event_copy_is_awaited_instead_of_left_after_the_response():
    assert "ctx.waitUntil(learner.pullEvents" not in WORKER
    assert "await learner.prepareOrigin()" in WORKER
    assert "response = await confirmEventDurability(" in WORKER
    transcribe = WORKER[WORKER.index('if (url.pathname === "/api/transcribe"'):]
    assert "const response = await confirmEventDurability(" in transcribe
    assert "heard, learner, url.pathname, prepared.cursor" in transcribe


def test_event_copy_only_confirms_after_reaching_the_reported_sequence():
    pull = _block("async pullEvents(")
    assert "await this.ensureRestored()" in pull
    assert "if (seen <= this.cursor) return true" in pull
    assert "if (this.cursor >= seen) return true" in pull
    assert "batch.length === 0" in pull and "return false" in pull
    assert "this.lastSeen = 0" in pull


def test_unchanged_reads_reuse_the_cursor_from_the_restore_gate():
    start = WORKER.index("async prepareOrigin(")
    prepare = WORKER[start:WORKER.index("private async restore(", start)]
    assert "await this.ensureRestored()" in prepare
    assert "cursor: this.cursor" in prepare
    confirm = _block("async function confirmEventDurability(")
    assert "let copied = seen <= knownCursor" in confirm


def test_an_unconfirmed_success_becomes_an_explicit_retriable_failure():
    confirm = _block("async function confirmEventDurability(")
    assert "EVENT_SYNC_ATTEMPTS" in confirm
    assert "if (!copied && response.ok)" in confirm
    failure = _block("function durabilityUnconfirmed(")
    assert 'status: 503' in failure
    assert '"retry-after": "2"' in failure
    assert '"x-eesti-durability": "unconfirmed"' in failure


def test_online_drill_reuses_its_event_id_when_the_learner_retries():
    render = _block("export function renderPracticeItem(", PATH_JS)
    assert "const eventId = tally.record ? crypto.randomUUID()" in render
    assert "event_id: eventId" in render
    assert "submittedGiven ??=" in render
    assert "given: submittedGiven" in render
    assert "latency_ms: submittedLatency" in render


def test_review_card_reuses_its_event_id_when_the_learner_retries():
    answer = _block("function wireAnswer(", REVIEW_JS)
    grading = _block("function wireGrading(", REVIEW_JS)
    assert "const eventId = crypto.randomUUID()" in answer
    assert "event_id: eventId" in answer
    assert "submittedGiven ??=" in answer
    assert "given: submittedGiven" in answer
    assert "submittedLatency ??=" in answer
    assert "latency_ms: submittedLatency" in answer
    assert "const eventId = crypto.randomUUID()" in grading
    assert "event_id: eventId" in grading
    assert "submittedRating ??=" in grading
    assert "rating: submittedRating" in grading
