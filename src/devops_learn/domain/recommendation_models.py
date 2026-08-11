"""Structured recommendations: see recommendations/service.py.

engineering_need and learning_value are tracked separately (see
docs/adr/0006-engineering-needs-vs-learning-objectives.md) so the platform can
say "this isn't strictly necessary for the workload, but you asked to learn
it" instead of silently merging the two justifications.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from devops_learn.domain.enums import RecommendationCategory


@dataclass(frozen=True)
class RecommendationAlternative:
    option: str
    why_not_preferred: str


@dataclass(frozen=True)
class Recommendation:
    id: str
    category: RecommendationCategory
    title: str
    recommendation: str
    reason: str
    alternatives: tuple[RecommendationAlternative, ...] = field(default_factory=tuple)
    recommended_option: str = "Accept"
    confidence: float = 1.0
    assumptions: tuple[str, ...] = field(default_factory=tuple)
    engineering_need: str = ""
    learning_value: str = ""
    cost_impact: str | None = None
    security_impact: str | None = None
    reliability_impact: str | None = None
    complexity_impact: str | None = None
    requires_user_decision: bool = False
