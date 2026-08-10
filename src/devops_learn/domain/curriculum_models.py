"""LearningProject -> Module -> Lesson -> Task content graph.

Instances are built once by curriculum/content_library.py builder functions and
are treated as immutable, shared reference data (not per-learner state).
Per-learner progress lives in domain/learner_models.py and domain/event_models.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from devops_learn.domain.content import ContentBlock, PredictionPrompt
from devops_learn.domain.enums import (
    CloudProviderKind,
    CompetencyCode,
    CompetencyState,
    LanguageTrackKind,
)


@dataclass(frozen=True)
class Hint:
    """One rung of a task's progressive hint ladder. level is 1-indexed."""

    level: int
    text: str


@dataclass(frozen=True)
class Challenge:
    """An optional stretch variation offered after a task, mainly at CHALLENGE level."""

    id: str
    title: str
    prompt: str


@dataclass(frozen=True)
class Checkpoint:
    """A milestone gating progression to the next module."""

    id: str
    title: str
    description: str
    required_competencies: tuple[tuple[CompetencyCode, CompetencyState], ...] = field(
        default_factory=tuple
    )


@dataclass(frozen=True)
class Task:
    """A single learner action: predict, attempt, validate, explain."""

    id: str
    title: str
    goal: str
    content: tuple[ContentBlock, ...]
    competency_codes: tuple[CompetencyCode, ...]
    hints: tuple[Hint, ...] = field(default_factory=tuple)
    full_explanation: ContentBlock | None = None
    prediction: PredictionPrompt | None = None
    challenge: Challenge | None = None


@dataclass(frozen=True)
class Lesson:
    id: str
    title: str
    content: tuple[ContentBlock, ...]
    tasks: tuple[Task, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class Module:
    id: str
    title: str
    why_it_matters: str
    lessons: tuple[Lesson, ...]
    competency_focus: tuple[CompetencyCode, ...] = field(default_factory=tuple)
    checkpoint: Checkpoint | None = None


@dataclass(frozen=True)
class LearningProject:
    id: str
    title: str
    description: str
    cloud: CloudProviderKind
    language: LanguageTrackKind
    modules: tuple[Module, ...]
