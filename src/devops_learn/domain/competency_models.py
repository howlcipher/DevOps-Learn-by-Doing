"""Competency catalog entries and per-learner competency state."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from devops_learn.domain.enums import CompetencyCode, CompetencyState


@dataclass(frozen=True)
class CompetencyDefinition:
    """Static catalog entry, not tied to any learner."""

    code: CompetencyCode
    title: str
    description: str


@dataclass(frozen=True)
class LearnerCompetency:
    """A learner's current state for one competency. Mutable over time via CompetencyService."""

    learner_id: int
    code: CompetencyCode
    state: CompetencyState
    updated_at: datetime
    evidence_event_id: int | None = None


@dataclass(frozen=True)
class CompetencyTransition:
    """Append-only record of one state change, so summaries never replay events."""

    learner_id: int
    code: CompetencyCode
    from_state: CompetencyState
    to_state: CompetencyState
    triggering_event_id: int
    occurred_at: datetime
    id: int | None = None
