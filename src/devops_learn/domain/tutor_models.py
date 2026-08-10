"""Structured outputs the tutor produces: recommendations and assessments.

These are canonical domain dataclasses. LLMProvider methods return them
directly rather than parallel DTOs; ai/types.py holds only response shapes
with no persisted identity (TutorExplanation, TroubleshootingFeedback,
LearningSummary, ArchitectureExplanation).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from devops_learn.domain.enums import CompetencyCode


@dataclass(frozen=True)
class RecommendationAlternative:
    option: str
    why_not_preferred: str


@dataclass(frozen=True)
class Recommendation:
    title: str
    recommendation: str
    reason: str
    learning_value: str
    alternatives: tuple[RecommendationAlternative, ...] = field(default_factory=tuple)
    security_impact: str | None = None
    cost_impact: str | None = None
    reliability_impact: str | None = None
    difficulty: str | None = None
    confidence: float = 1.0
    requires_confirmation: bool = False


@dataclass(frozen=True)
class Assessment:
    """Evaluation of one learner answer or attempt.

    is_correct is None for ungraded, reflective prompts (predictions, explain
    in your own words) where there is no single right answer.
    """

    task_id: str
    feedback: str
    is_correct: bool | None
    competency_signal: CompetencyCode | None = None
