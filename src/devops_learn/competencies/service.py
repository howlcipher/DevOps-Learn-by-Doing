"""Applies competency rules and persists resulting state and transition history."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime

from devops_learn.competencies.rules import (
    next_state,
    state_for_content_viewed,
    state_for_task_outcome,
)
from devops_learn.domain.competency_models import CompetencyTransition, LearnerCompetency
from devops_learn.domain.enums import (
    CompetencyCode,
    CompetencyState,
    LearningEventType,
    TaskOutcome,
)
from devops_learn.learning.journal import LearningJournal
from devops_learn.learning.persistence.repositories.competency_repository import (
    CompetencyRepository,
)


class CompetencyService:
    def __init__(
        self, competency_repository: CompetencyRepository, journal: LearningJournal
    ) -> None:
        self._competency_repository = competency_repository
        self._journal = journal

    def list_states(self, learner_id: int) -> list[LearnerCompetency]:
        return self._competency_repository.list_states(learner_id)

    def record_content_viewed(
        self,
        *,
        session_id: int,
        learner_id: int,
        codes: Iterable[CompetencyCode],
        triggering_event_id: int,
        occurred_at: datetime,
    ) -> list[LearnerCompetency]:
        candidate = state_for_content_viewed()
        return [
            self._apply(session_id, learner_id, code, candidate, triggering_event_id, occurred_at)
            for code in codes
        ]

    def record_task_outcome(
        self,
        *,
        session_id: int,
        learner_id: int,
        codes: Iterable[CompetencyCode],
        outcome: TaskOutcome,
        hints_used: int,
        total_hints: int,
        triggering_event_id: int,
        occurred_at: datetime,
    ) -> list[LearnerCompetency]:
        candidate = state_for_task_outcome(
            outcome, hints_used=hints_used, total_hints=total_hints
        )
        return [
            self._apply(session_id, learner_id, code, candidate, triggering_event_id, occurred_at)
            for code in codes
        ]

    def _apply(
        self,
        session_id: int,
        learner_id: int,
        code: CompetencyCode,
        candidate: CompetencyState,
        triggering_event_id: int,
        occurred_at: datetime,
    ) -> LearnerCompetency:
        existing = self._competency_repository.get_state(learner_id, code)
        current_state = existing.state if existing is not None else CompetencyState.NOT_STARTED
        new_state = next_state(current_state, candidate)

        updated = self._competency_repository.upsert_state(
            LearnerCompetency(
                learner_id=learner_id,
                code=code,
                state=new_state,
                updated_at=occurred_at,
                evidence_event_id=triggering_event_id,
            )
        )

        if new_state != current_state:
            self._competency_repository.record_transition(
                CompetencyTransition(
                    learner_id=learner_id,
                    code=code,
                    from_state=current_state,
                    to_state=new_state,
                    triggering_event_id=triggering_event_id,
                    occurred_at=occurred_at,
                )
            )
            self._journal.record(
                session_id=session_id,
                learner_id=learner_id,
                event_type=LearningEventType.COMPETENCY_ADVANCED,
                occurred_at=occurred_at,
                payload={
                    "competency": code.value,
                    "from_state": current_state.name,
                    "to_state": new_state.name,
                },
            )

        return updated
