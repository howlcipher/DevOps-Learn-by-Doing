"""Runs one troubleshooting attempt: hints, diagnosis submission, competency impact.

A wrong diagnosis never advances competency; see rules in competencies/rules.py
(state_for_task_outcome caps non-success outcomes at GUIDED) and the
"incomplete diagnosis does not advance competency" test. start/request_hint
delegate to learning/attempt_tracker.py, shared with regular curriculum tasks;
only diagnosis submission is specific to this service.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from devops_learn.competencies.service import CompetencyService
from devops_learn.domain.attempt_models import TaskAttempt
from devops_learn.domain.curriculum_models import Hint
from devops_learn.domain.enums import LearningEventType, TaskOutcome
from devops_learn.domain.troubleshooting_models import FailureScenario, Resolution
from devops_learn.learning.attempt_tracker import AttemptTracker
from devops_learn.learning.journal import LearningJournal
from devops_learn.learning.persistence.repositories.task_attempt_repository import (
    TaskAttemptRepository,
)


@dataclass(frozen=True)
class DiagnosisOutcome:
    is_correct: bool
    hints_used: int
    resolution: Resolution | None = None


class TroubleshootingService:
    def __init__(
        self,
        task_attempt_repository: TaskAttemptRepository,
        journal: LearningJournal,
        competency_service: CompetencyService,
    ) -> None:
        self._task_attempt_repository = task_attempt_repository
        self._journal = journal
        self._competency_service = competency_service
        self._attempt_tracker = AttemptTracker(task_attempt_repository, journal)

    def start(self, *, session_id: int, learner_id: int, task_id: str) -> TaskAttempt:
        return self._attempt_tracker.start(
            session_id=session_id, learner_id=learner_id, task_id=task_id
        )

    def request_hint(self, attempt: TaskAttempt, scenario: FailureScenario) -> Hint | None:
        return self._attempt_tracker.request_hint(attempt, scenario.hints)

    def submit_diagnosis(
        self, attempt: TaskAttempt, scenario: FailureScenario, diagnosis_key: str
    ) -> DiagnosisOutcome:
        assert attempt.id is not None
        hints_used = self._attempt_tracker.hints_used(attempt)
        is_correct = diagnosis_key == scenario.resolution.diagnosis_key
        now = datetime.now(timezone.utc)

        diagnosis_event = self._journal.record(
            session_id=attempt.session_id,
            learner_id=attempt.learner_id,
            event_type=LearningEventType.DIAGNOSIS_ATTEMPTED,
            occurred_at=now,
            task_id=attempt.task_id,
            payload={
                "diagnosis_key": diagnosis_key,
                "correct": is_correct,
                "hints_used": hints_used,
            },
        )
        assert diagnosis_event.id is not None

        if not is_correct:
            return DiagnosisOutcome(is_correct=False, hints_used=hints_used)

        self._task_attempt_repository.complete_attempt(
            attempt, completed_at=now, outcome=TaskOutcome.SUCCESS
        )
        self._journal.record(
            session_id=attempt.session_id,
            learner_id=attempt.learner_id,
            event_type=LearningEventType.TASK_COMPLETED,
            occurred_at=now,
            task_id=attempt.task_id,
        )
        self._competency_service.record_task_outcome(
            session_id=attempt.session_id,
            learner_id=attempt.learner_id,
            codes=scenario.competency_codes,
            outcome=TaskOutcome.SUCCESS,
            hints_used=hints_used,
            total_hints=len(scenario.hints),
            triggering_event_id=diagnosis_event.id,
            occurred_at=now,
        )
        return DiagnosisOutcome(
            is_correct=True, hints_used=hints_used, resolution=scenario.resolution
        )
