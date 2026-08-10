"""All SQL for the append-only learning_events journal is confined to this repository."""

from __future__ import annotations

import dataclasses
import json
import sqlite3
from datetime import datetime

from devops_learn.domain.enums import LearningEventType
from devops_learn.domain.event_models import LearningEvent


class EventRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def next_sequence_no(self, session_id: int) -> int:
        row = self._conn.execute(
            "SELECT COALESCE(MAX(sequence_no), 0) + 1 AS next FROM learning_events "
            "WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        return int(row["next"])

    def append(self, event: LearningEvent) -> LearningEvent:
        with self._conn:
            cursor = self._conn.execute(
                """
                INSERT INTO learning_events
                    (session_id, learner_id, sequence_no, event_type, occurred_at,
                     module_id, lesson_id, task_id, payload_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.session_id,
                    event.learner_id,
                    event.sequence_no,
                    event.event_type.value,
                    event.occurred_at.isoformat(),
                    event.module_id,
                    event.lesson_id,
                    event.task_id,
                    json.dumps(dict(event.payload)),
                ),
            )
        assert cursor.lastrowid is not None
        return dataclasses.replace(event, id=cursor.lastrowid)

    def list_for_session(self, session_id: int) -> list[LearningEvent]:
        rows = self._conn.execute(
            "SELECT * FROM learning_events WHERE session_id = ? ORDER BY sequence_no",
            (session_id,),
        ).fetchall()
        return [_row_to_event(row) for row in rows]

    def list_for_learner(self, learner_id: int) -> list[LearningEvent]:
        rows = self._conn.execute(
            "SELECT * FROM learning_events WHERE learner_id = ? ORDER BY id",
            (learner_id,),
        ).fetchall()
        return [_row_to_event(row) for row in rows]


def _row_to_event(row: sqlite3.Row) -> LearningEvent:
    return LearningEvent(
        id=row["id"],
        session_id=row["session_id"],
        learner_id=row["learner_id"],
        sequence_no=row["sequence_no"],
        event_type=LearningEventType(row["event_type"]),
        occurred_at=datetime.fromisoformat(row["occurred_at"]),
        module_id=row["module_id"],
        lesson_id=row["lesson_id"],
        task_id=row["task_id"],
        payload=json.loads(row["payload_json"]),
    )
