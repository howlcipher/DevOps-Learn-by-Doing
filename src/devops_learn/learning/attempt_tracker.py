"""Generic per-task attempt and hint-escalation tracking.

Shared by TroubleshootingService (diagnosis-specific on top) and
TutorOrchestrator (for a regular curriculum Task's hint ladder), so the
attempt/hint bookkeeping against sqlite exists in exactly one place.
"""

from __future__ import annotations

from datetime import datetime, timezone

from devops_learn.domain.attempt_models import HintUsage, TaskAttempt
from devops_learn.domain.curriculum_models import Hint
from devops_learn.domain.enums import LearningEventType
from devops_learn.learning.journal import LearningJournal
from devops_learn.learning.persistence.repositories.task_attempt_repository import (
    TaskAttemptRepository,
)


class AttemptTracker:
    def __init__(
        self, task_attempt_repository: TaskAttemptRepository, journal: LearningJournal
    ) -> None:
        self._task_attempt_repository = task_attempt_repository
        self._journal = journal

    def start(self, *, session_id: int, learner_id: int, task_id: str) -> TaskAttempt:
        now = datetime.now(timezone.utc)
        attempt_no = self._task_attempt_repository.next_attempt_no(session_id, task_id)
        attempt = self._task_attempt_repository.start_attempt(
            TaskAttempt(
                session_id=session_id,
                task_id=task_id,
                learner_id=learner_id,
                attempt_no=attempt_no,
                started_at=now,
            )
        )
        self._journal.record(
            session_id=session_id,
            learner_id=learner_id,
            event_type=LearningEventType.TASK_ATTEMPTED,
            occurred_at=now,
            task_id=task_id,
        )
        return attempt

    def get_or_start(self, *, session_id: int, learner_id: int, task_id: str) -> TaskAttempt:
        """Reuses the latest attempt for this task if it is still open,
        so repeated hint requests within one attempt don't create new rows."""
        existing = self._task_attempt_repository.latest_for_task(session_id, task_id)
        if existing is not None and existing.completed_at is None:
            return existing
        return self.start(session_id=session_id, learner_id=learner_id, task_id=task_id)

    def hints_used(self, attempt: TaskAttempt) -> int:
        assert attempt.id is not None
        return self._task_attempt_repository.count_hints_used(attempt.id)

    def request_hint(self, attempt: TaskAttempt, hints: tuple[Hint, ...]) -> Hint | None:
        assert attempt.id is not None
        used = self._task_attempt_repository.count_hints_used(attempt.id)
        if used >= len(hints):
            return None
        hint = hints[used]
        now = datetime.now(timezone.utc)
        event = self._journal.record(
            session_id=attempt.session_id,
            learner_id=attempt.learner_id,
            event_type=LearningEventType.HINT_REQUESTED,
            occurred_at=now,
            task_id=attempt.task_id,
            payload={"level": hint.level},
        )
        self._task_attempt_repository.record_hint_usage(
            HintUsage(
                task_attempt_id=attempt.id,
                hint_level=hint.level,
                requested_at=now,
                event_id=event.id,
            )
        )
        return hint
