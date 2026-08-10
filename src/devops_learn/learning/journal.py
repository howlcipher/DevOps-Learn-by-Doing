"""Thin wrapper so every caller records events the same way, sequence_no included."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping

from devops_learn.domain.enums import LearningEventType
from devops_learn.domain.event_models import LearningEvent
from devops_learn.learning.persistence.repositories.event_repository import EventRepository


class LearningJournal:
    def __init__(self, event_repository: EventRepository) -> None:
        self._event_repository = event_repository

    def record(
        self,
        *,
        session_id: int,
        learner_id: int,
        event_type: LearningEventType,
        occurred_at: datetime,
        module_id: str | None = None,
        lesson_id: str | None = None,
        task_id: str | None = None,
        payload: Mapping[str, Any] | None = None,
    ) -> LearningEvent:
        sequence_no = self._event_repository.next_sequence_no(session_id)
        event = LearningEvent(
            session_id=session_id,
            learner_id=learner_id,
            sequence_no=sequence_no,
            event_type=event_type,
            occurred_at=occurred_at,
            module_id=module_id,
            lesson_id=lesson_id,
            task_id=task_id,
            payload=payload or {},
        )
        return self._event_repository.append(event)
