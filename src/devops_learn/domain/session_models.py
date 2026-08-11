"""One engagement with the platform against one project: replaces the old
per-learner LearningSession, which assumed a fixed curriculum to walk."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from devops_learn.domain.enums import (
    CloudProviderKind,
    CostPriority,
    EnvironmentKind,
    ExecutionMode,
    ExplanationDepth,
)


@dataclass(frozen=True)
class EngagementSession:
    project_root: str
    mode: ExecutionMode
    explanation_depth: ExplanationDepth
    cloud: CloudProviderKind
    environment: EnvironmentKind
    cost_priority: CostPriority
    simulation_mode: bool
    started_at: datetime
    completed_at: datetime | None = None
    id: int | None = None
