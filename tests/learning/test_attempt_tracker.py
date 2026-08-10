import sqlite3

from devops_learn.domain.curriculum_models import Hint
from devops_learn.learning.attempt_tracker import AttemptTracker
from devops_learn.learning.journal import LearningJournal
from devops_learn.learning.persistence.repositories.event_repository import EventRepository
from devops_learn.learning.persistence.repositories.task_attempt_repository import (
    TaskAttemptRepository,
)

TASK_ID = "task_write_dockerfile"
HINTS = (
    Hint(level=1, text="Start FROM a slim base image."),
    Hint(level=2, text="Copy requirements.txt before the rest of the source."),
)


def _tracker(conn: sqlite3.Connection) -> AttemptTracker:
    return AttemptTracker(TaskAttemptRepository(conn), LearningJournal(EventRepository(conn)))


def test_hints_escalate_in_order_then_run_out(
    conn: sqlite3.Connection, seeded_session: tuple[int, int]
) -> None:
    learner_id, session_id = seeded_session
    tracker = _tracker(conn)
    attempt = tracker.start(session_id=session_id, learner_id=learner_id, task_id=TASK_ID)

    first = tracker.request_hint(attempt, HINTS)
    second = tracker.request_hint(attempt, HINTS)
    third = tracker.request_hint(attempt, HINTS)

    assert first is not None and first.level == 1
    assert second is not None and second.level == 2
    assert third is None
    assert tracker.hints_used(attempt) == 2
