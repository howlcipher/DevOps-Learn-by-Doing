"""All SQL for task_attempts and hint_usages is confined to this repository."""

from __future__ import annotations

import dataclasses
import sqlite3
from datetime import datetime

from devops_learn.domain.attempt_models import HintUsage, TaskAttempt
from devops_learn.domain.enums import TaskOutcome


class TaskAttemptRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def next_attempt_no(self, session_id: int, task_id: str) -> int:
        row = self._conn.execute(
            "SELECT COALESCE(MAX(attempt_no), 0) + 1 AS next FROM task_attempts "
            "WHERE session_id = ? AND task_id = ?",
            (session_id, task_id),
        ).fetchone()
        return int(row["next"])

    def start_attempt(self, attempt: TaskAttempt) -> TaskAttempt:
        with self._conn:
            cursor = self._conn.execute(
                """
                INSERT INTO task_attempts
                    (session_id, task_id, learner_id, attempt_no, started_at,
                     completed_at, outcome, hints_used_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    attempt.session_id,
                    attempt.task_id,
                    attempt.learner_id,
                    attempt.attempt_no,
                    attempt.started_at.isoformat(),
                    attempt.completed_at.isoformat() if attempt.completed_at else None,
                    attempt.outcome.value if attempt.outcome else None,
                    attempt.hints_used_count,
                ),
            )
        assert cursor.lastrowid is not None
        return dataclasses.replace(attempt, id=cursor.lastrowid)

    def get(self, attempt_id: int) -> TaskAttempt | None:
        row = self._conn.execute(
            "SELECT * FROM task_attempts WHERE id = ?", (attempt_id,)
        ).fetchone()
        return _row_to_attempt(row) if row is not None else None

    def latest_for_task(self, session_id: int, task_id: str) -> TaskAttempt | None:
        row = self._conn.execute(
            "SELECT * FROM task_attempts WHERE session_id = ? AND task_id = ? "
            "ORDER BY id DESC LIMIT 1",
            (session_id, task_id),
        ).fetchone()
        return _row_to_attempt(row) if row is not None else None

    def complete_attempt(
        self, attempt: TaskAttempt, *, completed_at: datetime, outcome: TaskOutcome
    ) -> TaskAttempt:
        assert attempt.id is not None
        updated = dataclasses.replace(attempt, completed_at=completed_at, outcome=outcome)
        with self._conn:
            self._conn.execute(
                "UPDATE task_attempts SET completed_at=?, outcome=? WHERE id=?",
                (completed_at.isoformat(), outcome.value, attempt.id),
            )
        return updated

    def record_hint_usage(self, usage: HintUsage) -> HintUsage:
        with self._conn:
            cursor = self._conn.execute(
                """
                INSERT INTO hint_usages (task_attempt_id, hint_level, requested_at, event_id)
                VALUES (?, ?, ?, ?)
                """,
                (
                    usage.task_attempt_id,
                    usage.hint_level,
                    usage.requested_at.isoformat(),
                    usage.event_id,
                ),
            )
            self._conn.execute(
                "UPDATE task_attempts SET hints_used_count = hints_used_count + 1 WHERE id = ?",
                (usage.task_attempt_id,),
            )
        assert cursor.lastrowid is not None
        return dataclasses.replace(usage, id=cursor.lastrowid)

    def count_hints_used(self, task_attempt_id: int) -> int:
        row = self._conn.execute(
            "SELECT hints_used_count FROM task_attempts WHERE id = ?", (task_attempt_id,)
        ).fetchone()
        return int(row["hints_used_count"]) if row is not None else 0


def _row_to_attempt(row: sqlite3.Row) -> TaskAttempt:
    return TaskAttempt(
        id=row["id"],
        session_id=row["session_id"],
        task_id=row["task_id"],
        learner_id=row["learner_id"],
        attempt_no=row["attempt_no"],
        started_at=datetime.fromisoformat(row["started_at"]),
        completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
        outcome=TaskOutcome(row["outcome"]) if row["outcome"] else None,
        hints_used_count=row["hints_used_count"],
    )
