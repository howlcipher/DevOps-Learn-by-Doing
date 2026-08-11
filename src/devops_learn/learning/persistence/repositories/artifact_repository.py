"""All SQL for generated artifacts is confined to this repository."""

from __future__ import annotations

import dataclasses
import sqlite3
from datetime import datetime

from devops_learn.domain.project_models import Artifact


class ArtifactRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def create(self, artifact: Artifact) -> Artifact:
        with self._conn:
            cursor = self._conn.execute(
                """
                INSERT INTO artifacts (session_id, artifact_type, path_or_ref, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    artifact.session_id,
                    artifact.artifact_type,
                    artifact.path_or_ref,
                    artifact.created_at.isoformat(),
                ),
            )
        assert cursor.lastrowid is not None
        return dataclasses.replace(artifact, id=cursor.lastrowid)

    def list_for_session(self, session_id: int) -> list[Artifact]:
        rows = self._conn.execute(
            "SELECT * FROM artifacts WHERE session_id = ? ORDER BY id ASC", (session_id,)
        ).fetchall()
        return [
            Artifact(
                id=row["id"],
                session_id=row["session_id"],
                artifact_type=row["artifact_type"],
                path_or_ref=row["path_or_ref"],
                created_at=datetime.fromisoformat(row["created_at"]),
            )
            for row in rows
        ]
