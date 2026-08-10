"""Direct id lookups return None for missing rows instead of raising."""

import sqlite3
from datetime import datetime, timezone

from devops_learn.domain.attempt_models import TaskAttempt
from devops_learn.domain.enums import SessionStatus, TaskOutcome
from devops_learn.learning.persistence.repositories.session_repository import SessionRepository
from devops_learn.learning.persistence.repositories.task_attempt_repository import (
    TaskAttemptRepository,
)

NOW = datetime(2026, 8, 9, 12, 0, 0, tzinfo=timezone.utc)


def test_session_get_round_trips_and_returns_none_for_a_missing_id(
    conn: sqlite3.Connection, seeded_session: tuple[int, int]
) -> None:
    _, session_id = seeded_session
    repository = SessionRepository(conn)

    stored = repository.get(session_id)

    assert stored is not None
    assert stored.id == session_id
    assert stored.status is SessionStatus.ACTIVE
    assert repository.get(session_id + 1000) is None


def test_task_attempt_get_round_trips_and_returns_none_for_a_missing_id(
    conn: sqlite3.Connection, seeded_session: tuple[int, int]
) -> None:
    learner_id, session_id = seeded_session
    repository = TaskAttemptRepository(conn)
    created = repository.start_attempt(
        TaskAttempt(
            session_id=session_id,
            learner_id=learner_id,
            task_id="task_write_dockerfile",
            attempt_no=1,
            started_at=NOW,
            completed_at=NOW,
            outcome=TaskOutcome.PARTIAL,
        )
    )
    assert created.id is not None

    stored = repository.get(created.id)

    assert stored is not None
    assert stored.task_id == "task_write_dockerfile"
    assert stored.outcome is TaskOutcome.PARTIAL
    assert stored.completed_at == NOW
    assert repository.get(created.id + 1000) is None
