"""One deliberate-failure / troubleshooting scenario's static content shape.

Per-attempt state (which sources were inspected, hints used, final diagnosis)
is tracked by troubleshooting/service.py and journaled as LearningEvents, not
stored on these dataclasses, which are immutable authored content.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from devops_learn.domain.curriculum_models import Hint
from devops_learn.domain.enums import CompetencyCode


@dataclass(frozen=True)
class EvidenceSource:
    """One thing the learner can choose to inspect (e.g. container logs)."""

    id: str
    label: str
    evidence_text: str
    is_relevant: bool


@dataclass(frozen=True)
class TroubleshootingStep:
    """One 'what should you inspect?' decision point, offering several sources."""

    prompt: str
    sources: tuple[EvidenceSource, ...]


@dataclass(frozen=True)
class Diagnosis:
    """One candidate root-cause the learner may select as their final answer."""

    key: str
    label: str
    is_correct: bool


@dataclass(frozen=True)
class Resolution:
    diagnosis_key: str
    explanation: str
    fix_summary: str


@dataclass(frozen=True)
class FailureScenario:
    id: str
    title: str
    narrative: str
    steps: tuple[TroubleshootingStep, ...]
    candidate_diagnoses: tuple[Diagnosis, ...]
    resolution: Resolution
    competency_codes: tuple[CompetencyCode, ...]
    hints: tuple[Hint, ...] = field(default_factory=tuple)
