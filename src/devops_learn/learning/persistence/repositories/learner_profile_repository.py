"""All SQL for learner_profiles is confined to this repository."""

from __future__ import annotations

import json
import sqlite3

from devops_learn.domain.learner_profile_models import (
    CompetencyArea,
    LearnerProfile,
    ProficiencyLevel,
)


class LearnerProfileRepository:
    _ROW_ID = 1

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def load(self) -> LearnerProfile | None:
        row = self._conn.execute(
            "SELECT proficiencies_json, focus_json FROM learner_profiles WHERE id = ?",
            (self._ROW_ID,),
        ).fetchone()
        if row is None:
            return None
        proficiencies = {
            CompetencyArea(k): ProficiencyLevel(v)
            for k, v in json.loads(row["proficiencies_json"] or "{}").items()
        }
        focus = tuple(
            CompetencyArea(v) for v in json.loads(row["focus_json"] or "[]")
        )
        return LearnerProfile(proficiencies=proficiencies, learning_focus=focus)

    def save(self, profile: LearnerProfile) -> LearnerProfile:
        proficiencies_json = json.dumps(
            {area.value: level.value for area, level in profile.proficiencies.items()}
        )
        focus_json = json.dumps([area.value for area in profile.learning_focus])
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO learner_profiles (id, proficiencies_json, focus_json)
                VALUES (?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    proficiencies_json = excluded.proficiencies_json,
                    focus_json = excluded.focus_json
                """,
                (self._ROW_ID, proficiencies_json, focus_json),
            )
        return profile
