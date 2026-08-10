"""LLM-facing response DTOs with no persisted identity.

These are distinct from the canonical domain dataclasses (Hint, Recommendation,
Assessment in domain/), which LLMProvider methods return directly. Everything
here is either purely generated text (TutorExplanation, ArchitectureExplanation,
TroubleshootingFeedback) or, for LearningSummary, a deterministic structure
computed by learning/summary_service.py from persisted data, optionally
narrated by an LLMProvider but never invented by one.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from devops_learn.domain.enums import CompetencyCode


@dataclass(frozen=True)
class TutorExplanation:
    title: str
    body: str
    related_competencies: tuple[CompetencyCode, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class TroubleshootingFeedback:
    is_on_track: bool
    message: str
    suggested_next_source_id: str | None = None


@dataclass(frozen=True)
class LearningSummary:
    """Computed deterministically by learning/summary_service.py from real data."""

    learner_id: int
    generated_at: datetime
    competency_lines: tuple[str, ...]
    narrative_lines: tuple[str, ...]
    recommended_next_step: str


@dataclass(frozen=True)
class ArchitectureExplanation:
    title: str
    body: str
    diagram_hint: str | None = None
