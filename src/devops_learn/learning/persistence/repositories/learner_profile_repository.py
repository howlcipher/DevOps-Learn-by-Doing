"""All SQL for learner_profiles is confined to this repository."""

from __future__ import annotations

import dataclasses
import sqlite3
from datetime import datetime

from devops_learn.domain.enums import (
    AssistanceLevel,
    CloudProviderKind,
    ExplanationDepth,
    LanguageTrackKind,
)
from devops_learn.domain.learner_models import LearnerProfile


class LearnerProfileRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def create(self, profile: LearnerProfile) -> LearnerProfile:
        with self._conn:
            cursor = self._conn.execute(
                """
                INSERT INTO learner_profiles
                    (display_name, cloud_provider, language_track, assistance_level,
                     explanation_depth, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    profile.display_name,
                    profile.cloud_provider.value,
                    profile.language_track.value,
                    profile.assistance_level.name,
                    profile.explanation_depth.name,
                    profile.created_at.isoformat(),
                    profile.updated_at.isoformat(),
                ),
            )
        assert cursor.lastrowid is not None
        return dataclasses.replace(profile, id=cursor.lastrowid)

    def get(self, learner_id: int) -> LearnerProfile | None:
        row = self._conn.execute(
            "SELECT * FROM learner_profiles WHERE id = ?", (learner_id,)
        ).fetchone()
        return _row_to_profile(row) if row is not None else None

    def latest(self) -> LearnerProfile | None:
        row = self._conn.execute(
            "SELECT * FROM learner_profiles ORDER BY id DESC LIMIT 1"
        ).fetchone()
        return _row_to_profile(row) if row is not None else None

    def update(self, profile: LearnerProfile) -> LearnerProfile:
        assert profile.id is not None
        with self._conn:
            self._conn.execute(
                """
                UPDATE learner_profiles
                SET display_name=?, cloud_provider=?, language_track=?, assistance_level=?,
                    explanation_depth=?, updated_at=?
                WHERE id=?
                """,
                (
                    profile.display_name,
                    profile.cloud_provider.value,
                    profile.language_track.value,
                    profile.assistance_level.name,
                    profile.explanation_depth.name,
                    profile.updated_at.isoformat(),
                    profile.id,
                ),
            )
        return profile


def _row_to_profile(row: sqlite3.Row) -> LearnerProfile:
    return LearnerProfile(
        id=row["id"],
        display_name=row["display_name"],
        cloud_provider=CloudProviderKind(row["cloud_provider"]),
        language_track=LanguageTrackKind(row["language_track"]),
        assistance_level=AssistanceLevel[row["assistance_level"]],
        explanation_depth=ExplanationDepth[row["explanation_depth"]],
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
    )
