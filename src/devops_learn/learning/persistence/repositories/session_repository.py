"""All SQL for learning_sessions is confined to this repository.

current_* columns are the live resume pointer; resume reads this row directly
and never replays learning_events to reconstruct position.
"""

from __future__ import annotations

import dataclasses
import sqlite3
from datetime import datetime

from devops_learn.domain.enums import SessionStatus
from devops_learn.domain.learner_models import LearningSession


class SessionRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def create(self, session: LearningSession) -> LearningSession:
        with self._conn:
            cursor = self._conn.execute(
                """
                INSERT INTO learning_sessions
                    (learner_id, project_id, status, current_module_id, current_lesson_id,
                     current_task_id, simulation_mode, started_at, last_active_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session.learner_id,
                    session.project_id,
                    session.status.value,
                    session.current_module_id,
                    session.current_lesson_id,
                    session.current_task_id,
                    int(session.simulation_mode),
                    session.started_at.isoformat(),
                    session.last_active_at.isoformat(),
                ),
            )
        assert cursor.lastrowid is not None
        return dataclasses.replace(session, id=cursor.lastrowid)

    def get(self, session_id: int) -> LearningSession | None:
        row = self._conn.execute(
            "SELECT * FROM learning_sessions WHERE id = ?", (session_id,)
        ).fetchone()
        return _row_to_session(row) if row is not None else None

    def latest_active_for_learner(self, learner_id: int) -> LearningSession | None:
        row = self._conn.execute(
            """
            SELECT * FROM learning_sessions
            WHERE learner_id = ? AND status = ?
            ORDER BY id DESC LIMIT 1
            """,
            (learner_id, SessionStatus.ACTIVE.value),
        ).fetchone()
        return _row_to_session(row) if row is not None else None

    def update_pointer(self, session: LearningSession) -> LearningSession:
        assert session.id is not None
        with self._conn:
            self._conn.execute(
                """
                UPDATE learning_sessions
                SET status=?, current_module_id=?, current_lesson_id=?, current_task_id=?,
                    last_active_at=?
                WHERE id=?
                """,
                (
                    session.status.value,
                    session.current_module_id,
                    session.current_lesson_id,
                    session.current_task_id,
                    session.last_active_at.isoformat(),
                    session.id,
                ),
            )
        return session


def _row_to_session(row: sqlite3.Row) -> LearningSession:
    return LearningSession(
        id=row["id"],
        learner_id=row["learner_id"],
        project_id=row["project_id"],
        status=SessionStatus(row["status"]),
        current_module_id=row["current_module_id"],
        current_lesson_id=row["current_lesson_id"],
        current_task_id=row["current_task_id"],
        simulation_mode=bool(row["simulation_mode"]),
        started_at=datetime.fromisoformat(row["started_at"]),
        last_active_at=datetime.fromisoformat(row["last_active_at"]),
    )
