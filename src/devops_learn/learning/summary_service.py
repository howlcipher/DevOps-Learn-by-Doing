"""Builds a LearningSummary deterministically from persisted competency and event data.

No AI call is required to produce a correct summary; an LLMProvider may later
narrate these lines in friendlier prose, but the underlying facts always come
from here, never from the model.
"""

from __future__ import annotations

from datetime import datetime, timezone

from devops_learn.ai.types import LearningSummary
from devops_learn.domain.competency_models import LearnerCompetency
from devops_learn.domain.enums import CompetencyState, LearningEventType
from devops_learn.domain.event_models import LearningEvent
from devops_learn.learning.persistence.repositories.competency_repository import (
    CompetencyRepository,
)
from devops_learn.learning.persistence.repositories.event_repository import EventRepository


class SummaryService:
    def __init__(
        self, competency_repository: CompetencyRepository, event_repository: EventRepository
    ) -> None:
        self._competency_repository = competency_repository
        self._event_repository = event_repository

    def build_summary(self, learner_id: int) -> LearningSummary:
        states = self._competency_repository.list_states(learner_id)
        events = self._event_repository.list_for_learner(learner_id)
        return LearningSummary(
            learner_id=learner_id,
            generated_at=datetime.now(timezone.utc),
            competency_lines=_competency_lines(states),
            narrative_lines=_narrative_lines(events),
            recommended_next_step=_recommend_next_step(states),
        )


def _competency_lines(states: list[LearnerCompetency]) -> tuple[str, ...]:
    if not states:
        return ("No competencies tracked yet.",)
    return tuple(f"{s.code.value}: {s.state.name.title()}" for s in states)


def _narrative_lines(events: list[LearningEvent]) -> tuple[str, ...]:
    lines: list[str] = []

    completed_modules = [e for e in events if e.event_type == LearningEventType.MODULE_COMPLETED]
    if completed_modules:
        lines.append(f"You completed {len(completed_modules)} module(s).")

    for event in events:
        if event.event_type != LearningEventType.DIAGNOSIS_ATTEMPTED:
            continue
        if not event.payload.get("correct"):
            continue
        hints_used = event.payload.get("hints_used", 0)
        lines.append(f"You diagnosed one failure with {hints_used} hint(s).")

    if not lines:
        lines.append("No activity recorded yet.")
    return tuple(lines)


def _recommend_next_step(states: list[LearnerCompetency]) -> str:
    not_demonstrated = [s for s in states if s.state != CompetencyState.DEMONSTRATED]
    if not not_demonstrated:
        return "Continue to the next module."
    weakest = min(not_demonstrated, key=lambda s: s.state)
    return f"Continue practicing {weakest.code.value} before moving on."
