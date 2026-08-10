"""Per-attempt task state: how many times, how many hints, what outcome.

Backs progressive hint escalation tracking and feeds competency scoring; not
part of the static curriculum content graph in curriculum_models.py.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from devops_learn.domain.enums import TaskOutcome


@dataclass(frozen=True)
class TaskAttempt:
    session_id: int
    task_id: str
    learner_id: int
    attempt_no: int
    started_at: datetime
    completed_at: datetime | None = None
    outcome: TaskOutcome | None = None
    hints_used_count: int = 0
    id: int | None = None


@dataclass(frozen=True)
class HintUsage:
    task_attempt_id: int
    hint_level: int
    requested_at: datetime
    event_id: int | None = None
    id: int | None = None
