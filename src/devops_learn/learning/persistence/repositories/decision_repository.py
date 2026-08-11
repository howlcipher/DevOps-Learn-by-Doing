"""All SQL for the decisions table (human answers/approvals of questions and
recommendations, distinct from tool-level ApprovalRecord in tools/approval.py)."""

from __future__ import annotations

import dataclasses
import sqlite3
from datetime import datetime

from devops_learn.domain.question_models import Decision


class DecisionRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def record(self, session_id: int, decision: Decision) -> Decision:
        with self._conn:
            cursor = self._conn.execute(
                """
                INSERT INTO decisions
                    (session_id, subject_kind, subject_id, outcome, detail, decided_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    decision.subject_kind,
                    decision.subject_id,
                    decision.outcome,
                    decision.detail,
                    decision.decided_at.isoformat(),
                ),
            )
        assert cursor.lastrowid is not None
        return dataclasses.replace(decision, id=cursor.lastrowid)

    def list_for_session(self, session_id: int) -> list[Decision]:
        rows = self._conn.execute(
            "SELECT * FROM decisions WHERE session_id = ? ORDER BY id ASC", (session_id,)
        ).fetchall()
        return [
            Decision(
                id=row["id"],
                subject_kind=row["subject_kind"],
                subject_id=row["subject_id"],
                outcome=row["outcome"],
                detail=row["detail"],
                decided_at=datetime.fromisoformat(row["decided_at"]),
            )
            for row in rows
        ]
