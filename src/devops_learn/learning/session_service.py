"""Session lifecycle: start, resume, advance pointer, complete.

resume is O(1): it reads the session row's current_* columns directly and
never reconstructs position by replaying learning_events.
"""

from __future__ import annotations

import dataclasses
from datetime import datetime, timezone

from devops_learn.domain.enums import LearningEventType, SessionStatus
from devops_learn.domain.learner_models import LearningSession
from devops_learn.learning.journal import LearningJournal
from devops_learn.learning.persistence.repositories.session_repository import SessionRepository


class SessionService:
    def __init__(self, session_repository: SessionRepository, journal: LearningJournal) -> None:
        self._session_repository = session_repository
        self._journal = journal

    def start_new_session(
        self, learner_id: int, project_id: str, *, simulation_mode: bool
    ) -> LearningSession:
        now = datetime.now(timezone.utc)
        session = LearningSession(
            learner_id=learner_id,
            project_id=project_id,
            status=SessionStatus.ACTIVE,
            simulation_mode=simulation_mode,
            started_at=now,
            last_active_at=now,
        )
        session = self._session_repository.create(session)
        assert session.id is not None
        self._journal.record(
            session_id=session.id,
            learner_id=learner_id,
            event_type=LearningEventType.SESSION_STARTED,
            occurred_at=now,
        )
        return session

    def resume_latest(self, learner_id: int) -> LearningSession | None:
        session = self._session_repository.latest_active_for_learner(learner_id)
        if session is None:
            return None
        assert session.id is not None
        now = datetime.now(timezone.utc)
        updated = self._session_repository.update_pointer(
            dataclasses.replace(session, last_active_at=now)
        )
        self._journal.record(
            session_id=session.id,
            learner_id=learner_id,
            event_type=LearningEventType.SESSION_RESUMED,
            occurred_at=now,
        )
        return updated

    def advance_pointer(
        self,
        session: LearningSession,
        *,
        module_id: str | None,
        lesson_id: str | None,
        task_id: str | None,
    ) -> LearningSession:
        updated = dataclasses.replace(
            session,
            current_module_id=module_id,
            current_lesson_id=lesson_id,
            current_task_id=task_id,
            last_active_at=datetime.now(timezone.utc),
        )
        return self._session_repository.update_pointer(updated)

    def complete_session(self, session: LearningSession) -> LearningSession:
        updated = dataclasses.replace(
            session, status=SessionStatus.COMPLETED, last_active_at=datetime.now(timezone.utc)
        )
        return self._session_repository.update_pointer(updated)
