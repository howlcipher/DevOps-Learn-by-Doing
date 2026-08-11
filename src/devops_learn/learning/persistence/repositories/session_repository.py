"""All SQL for engagement_sessions is confined to this repository."""

from __future__ import annotations

import dataclasses
import sqlite3
from datetime import datetime

from devops_learn.domain.enums import (
    CloudProviderKind,
    CostPriority,
    EnvironmentKind,
    ExplanationDepth,
    OperatingMode,
)
from devops_learn.domain.session_models import EngagementSession


class SessionRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def create(self, session: EngagementSession) -> EngagementSession:
        with self._conn:
            cursor = self._conn.execute(
                """
                INSERT INTO engagement_sessions
                    (project_root, mode, explanation_depth, cloud, environment,
                     cost_priority, simulation_mode, started_at, completed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session.project_root,
                    session.mode.value,
                    session.explanation_depth.name,
                    session.cloud.value,
                    session.environment.value,
                    session.cost_priority.value,
                    int(session.simulation_mode),
                    session.started_at.isoformat(),
                    session.completed_at.isoformat() if session.completed_at else None,
                ),
            )
        assert cursor.lastrowid is not None
        return dataclasses.replace(session, id=cursor.lastrowid)

    def get(self, session_id: int) -> EngagementSession | None:
        row = self._conn.execute(
            "SELECT * FROM engagement_sessions WHERE id = ?", (session_id,)
        ).fetchone()
        return _row_to_session(row) if row is not None else None

    def latest(self) -> EngagementSession | None:
        row = self._conn.execute(
            "SELECT * FROM engagement_sessions ORDER BY id DESC LIMIT 1"
        ).fetchone()
        return _row_to_session(row) if row is not None else None

    def complete(self, session: EngagementSession, *, completed_at: datetime) -> EngagementSession:
        assert session.id is not None
        with self._conn:
            self._conn.execute(
                "UPDATE engagement_sessions SET completed_at = ? WHERE id = ?",
                (completed_at.isoformat(), session.id),
            )
        return dataclasses.replace(session, completed_at=completed_at)


def _row_to_session(row: sqlite3.Row) -> EngagementSession:
    return EngagementSession(
        id=row["id"],
        project_root=row["project_root"],
        mode=OperatingMode(row["mode"]),
        explanation_depth=ExplanationDepth[row["explanation_depth"]],
        cloud=CloudProviderKind(row["cloud"]),
        environment=EnvironmentKind(row["environment"]),
        cost_priority=CostPriority(row["cost_priority"]),
        simulation_mode=bool(row["simulation_mode"]),
        started_at=datetime.fromisoformat(row["started_at"]),
        completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
    )
