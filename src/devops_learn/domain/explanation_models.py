"""Explanation and LearningMoment: the platform's explainability primitives.

Explanation follows the fixed ACTION/WHY/DECISION/ALTERNATIVES/TRADEOFF/
WHAT_TO_UNDERSTAND/RESULT shape used throughout the product spec, so
presenters never improvise structure per call site. Not every field is
required: trivial actions should use fewer fields rather than padding all of
them (see docs/architecture.md#explainability).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Explanation:
    action: str
    why: str | None = None
    decision: str | None = None
    alternatives: str | None = None
    tradeoff: str | None = None
    what_to_understand: str | None = None
    result: str | None = None


@dataclass(frozen=True)
class LearningMoment:
    concept: str
    trigger: str
    summary: str
    deep_explanation: str
    why_it_matters: str
    related_action: str | None = None
    related_artifact: str | None = None
    optional_question: str | None = None
