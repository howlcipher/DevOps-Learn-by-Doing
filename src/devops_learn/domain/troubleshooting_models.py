"""Troubleshooting evidence and diagnosis.

Evidence is gathered from real ToolResult output (or, in simulation mode,
simulated ToolResult output) rather than authored curriculum content: see
troubleshooting/service.py and docs/architecture.md#troubleshooting. The
platform never asks the AI to diagnose from a one-line failure description
alone; it always assembles EvidenceItem entries first.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Mapping

from devops_learn.domain.learner_profile_models import CompetencyArea


class HintLevel(IntEnum):
    """Progressive assistance levels (0 to 4)."""

    EVIDENCE = 0
    INSPECTION = 1
    SUBSYSTEM = 2
    ROOT_CAUSE = 3
    REMEDIATION = 4


@dataclass(frozen=True)
class EvidenceItem:
    source: str  # e.g. "kubernetes.describe", "kubernetes.logs"
    content: str
    is_relevant: bool = False


@dataclass(frozen=True)
class FailureEvent:
    title: str
    narrative: str
    evidence: tuple[EvidenceItem, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class Diagnosis:
    likely_cause: str
    explanation: str
    recommended_fix: str
    learning_moment: str | None = None


@dataclass(frozen=True)
class Observation:
    """Factual, deterministic tool output or system measurement."""

    source: str  # e.g. "docker.logs", "http_probe", "socket_status", "container_exit"
    content: str
    exit_code: int | None = None
    is_error: bool = False
    details: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Interpretation:
    """Analytical deduction separated from raw observation."""

    observation_summary: str
    likely_subsystem: str
    hypothesis: str
    confidence: float = 1.0


@dataclass(frozen=True)
class RemediationAttempt:
    """Learner's proposed operational or configuration fix."""

    scenario_id: str
    action: str
    parameters: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class VerificationResult:
    """Deterministic recovery verification outcome."""

    success: bool
    summary: str
    observations: tuple[Observation, ...] = field(default_factory=tuple)
    is_live: bool = False
    details: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TroubleshootingEvidence:
    """Complete ledger of troubleshooting investigation and recovery."""

    scenario_id: str
    before_state: tuple[Observation, ...]
    remediation: RemediationAttempt | None = None
    after_state: tuple[Observation, ...] = field(default_factory=tuple)
    verification: VerificationResult | None = None
    resolved: bool = False
    mode_label: str = "(simulated)"


@dataclass(frozen=True)
class TroubleshootingScenario:
    """Specification of a bounded troubleshooting problem."""

    scenario_id: str
    title: str
    learning_objective: str
    category: CompetencyArea
    fault_description: str
    expected_symptoms: tuple[str, ...]
    allowed_diagnostic_tools: tuple[str, ...]
    hints: Mapping[int, str]
    success_criteria: str
    cleanup_requirements: str


@dataclass(frozen=True)
class TroubleshootingSession:
    """Active troubleshooting scenario lifecycle state."""

    scenario: TroubleshootingScenario
    is_live: bool
    project_root: str
    evidence: TroubleshootingEvidence
    active: bool = True
