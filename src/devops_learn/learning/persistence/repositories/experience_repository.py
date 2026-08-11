"""All SQL for experience_entries (the evidence log; see domain/experience_models.py)."""

from __future__ import annotations

import dataclasses
import sqlite3
from datetime import datetime

from devops_learn.domain.enums import ExperienceState
from devops_learn.domain.experience_models import ExperienceEntry


class ExperienceRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def record(self, entry: ExperienceEntry) -> ExperienceEntry:
        with self._conn:
            cursor = self._conn.execute(
                """
                INSERT INTO experience_entries (session_id, concept, item, state, occurred_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(session_id, concept, item) DO UPDATE SET
                    state = excluded.state, occurred_at = excluded.occurred_at
                """,
                (
                    entry.session_id,
                    entry.concept,
                    entry.item,
                    entry.state.value,
                    entry.occurred_at.isoformat(),
                ),
            )
        row_id = cursor.lastrowid
        if not row_id:
            row = self._conn.execute(
                "SELECT id FROM experience_entries WHERE session_id=? AND concept=? AND item=?",
                (entry.session_id, entry.concept, entry.item),
            ).fetchone()
            row_id = row["id"]
        return dataclasses.replace(entry, id=row_id)

    def list_for_session(self, session_id: int) -> list[ExperienceEntry]:
        rows = self._conn.execute(
            "SELECT * FROM experience_entries WHERE session_id = ? ORDER BY id ASC",
            (session_id,),
        ).fetchall()
        return [
            ExperienceEntry(
                id=row["id"],
                session_id=row["session_id"],
                concept=row["concept"],
                item=row["item"],
                state=ExperienceState(row["state"]),
                occurred_at=datetime.fromisoformat(row["occurred_at"]),
            )
            for row in rows
        ]
