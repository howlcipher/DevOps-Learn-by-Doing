"""Per-learner identity and session pointer state.

Instances are immutable value objects; updates go through repositories via
dataclasses.replace(...), not in-place mutation, matching the rest of domain/.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from devops_learn.domain.enums import (
    AssistanceLevel,
    CloudProviderKind,
    ExplanationDepth,
    LanguageTrackKind,
    SessionStatus,
)


@dataclass(frozen=True)
class LearnerProfile:
    display_name: str
    cloud_provider: CloudProviderKind
    language_track: LanguageTrackKind
    assistance_level: AssistanceLevel
    explanation_depth: ExplanationDepth
    created_at: datetime
    updated_at: datetime
    id: int | None = None


@dataclass(frozen=True)
class LearningSession:
    """current_* columns are the live resume pointer; do not derive them from events."""

    learner_id: int
    project_id: str
    status: SessionStatus
    simulation_mode: bool
    started_at: datetime
    last_active_at: datetime
    current_module_id: str | None = None
    current_lesson_id: str | None = None
    current_task_id: str | None = None
    id: int | None = None
