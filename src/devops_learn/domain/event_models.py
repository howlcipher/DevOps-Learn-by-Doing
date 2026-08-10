"""Append-only learning history / audit journal entries."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Mapping

from devops_learn.domain.enums import LearningEventType


@dataclass(frozen=True)
class LearningEvent:
    """One journal entry. payload holds event-specific detail, serialized as JSON."""

    session_id: int
    learner_id: int
    sequence_no: int
    event_type: LearningEventType
    occurred_at: datetime
    module_id: str | None = None
    lesson_id: str | None = None
    task_id: str | None = None
    payload: Mapping[str, Any] = field(default_factory=dict)
    id: int | None = None
