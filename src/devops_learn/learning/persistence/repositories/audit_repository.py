"""All SQL for the append-only audit_events journal."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime

from devops_learn.domain.audit_models import AuditEvent
from devops_learn.domain.enums import AuditEventType


class AuditRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def next_sequence_no(self, session_id: int) -> int:
        row = self._conn.execute(
            "SELECT COALESCE(MAX(sequence_no), 0) AS m FROM audit_events WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        return int(row["m"]) + 1

    def append(self, event: AuditEvent) -> AuditEvent:
        with self._conn:
            cursor = self._conn.execute(
                """
                INSERT INTO audit_events
                    (session_id, sequence_no, event_type, occurred_at, summary, payload_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    event.session_id,
                    event.sequence_no,
                    event.event_type.value,
                    event.occurred_at.isoformat(),
                    event.summary,
                    json.dumps(event.payload),
                ),
            )
        assert cursor.lastrowid is not None
        return AuditEvent(
            id=cursor.lastrowid,
            session_id=event.session_id,
            sequence_no=event.sequence_no,
            event_type=event.event_type,
            occurred_at=event.occurred_at,
            summary=event.summary,
            payload=event.payload,
        )

    def list_for_session(self, session_id: int) -> list[AuditEvent]:
        rows = self._conn.execute(
            "SELECT * FROM audit_events WHERE session_id = ? ORDER BY sequence_no ASC",
            (session_id,),
        ).fetchall()
        return [_row_to_event(row) for row in rows]


def _row_to_event(row: sqlite3.Row) -> AuditEvent:
    return AuditEvent(
        id=row["id"],
        session_id=row["session_id"],
        sequence_no=row["sequence_no"],
        event_type=AuditEventType(row["event_type"]),
        occurred_at=datetime.fromisoformat(row["occurred_at"]),
        summary=row["summary"],
        payload=json.loads(row["payload_json"]),
    )
