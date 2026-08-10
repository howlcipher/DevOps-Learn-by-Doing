"""All SQL for competency_states and competency_transitions is confined here.

competency_states holds current, mutable state; competency_transitions is an
append-only history so summaries never have to reverse-engineer payload_json.
"""

from __future__ import annotations

import dataclasses
import sqlite3
from datetime import datetime

from devops_learn.domain.competency_models import CompetencyTransition, LearnerCompetency
from devops_learn.domain.enums import CompetencyCode, CompetencyState


class CompetencyRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def get_state(self, learner_id: int, code: CompetencyCode) -> LearnerCompetency | None:
        row = self._conn.execute(
            "SELECT * FROM competency_states WHERE learner_id = ? AND competency_code = ?",
            (learner_id, code.value),
        ).fetchone()
        return _row_to_competency(row) if row is not None else None

    def list_states(self, learner_id: int) -> list[LearnerCompetency]:
        rows = self._conn.execute(
            "SELECT * FROM competency_states WHERE learner_id = ? ORDER BY competency_code",
            (learner_id,),
        ).fetchall()
        return [_row_to_competency(row) for row in rows]

    def upsert_state(self, competency: LearnerCompetency) -> LearnerCompetency:
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO competency_states
                    (learner_id, competency_code, state, updated_at, evidence_event_id)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(learner_id, competency_code) DO UPDATE SET
                    state=excluded.state,
                    updated_at=excluded.updated_at,
                    evidence_event_id=excluded.evidence_event_id
                """,
                (
                    competency.learner_id,
                    competency.code.value,
                    competency.state.name,
                    competency.updated_at.isoformat(),
                    competency.evidence_event_id,
                ),
            )
        return competency

    def record_transition(self, transition: CompetencyTransition) -> CompetencyTransition:
        with self._conn:
            cursor = self._conn.execute(
                """
                INSERT INTO competency_transitions
                    (learner_id, competency_code, from_state, to_state,
                     triggering_event_id, occurred_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    transition.learner_id,
                    transition.code.value,
                    transition.from_state.name,
                    transition.to_state.name,
                    transition.triggering_event_id,
                    transition.occurred_at.isoformat(),
                ),
            )
        assert cursor.lastrowid is not None
        return dataclasses.replace(transition, id=cursor.lastrowid)

    def list_transitions(self, learner_id: int) -> list[CompetencyTransition]:
        rows = self._conn.execute(
            "SELECT * FROM competency_transitions WHERE learner_id = ? ORDER BY id",
            (learner_id,),
        ).fetchall()
        return [_row_to_transition(row) for row in rows]


def _row_to_competency(row: sqlite3.Row) -> LearnerCompetency:
    return LearnerCompetency(
        learner_id=row["learner_id"],
        code=CompetencyCode(row["competency_code"]),
        state=CompetencyState[row["state"]],
        updated_at=datetime.fromisoformat(row["updated_at"]),
        evidence_event_id=row["evidence_event_id"],
    )


def _row_to_transition(row: sqlite3.Row) -> CompetencyTransition:
    return CompetencyTransition(
        id=row["id"],
        learner_id=row["learner_id"],
        code=CompetencyCode(row["competency_code"]),
        from_state=CompetencyState[row["from_state"]],
        to_state=CompetencyState[row["to_state"]],
        triggering_event_id=row["triggering_event_id"],
        occurred_at=datetime.fromisoformat(row["occurred_at"]),
    )
