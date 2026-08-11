"""Troubleshooting evidence and diagnosis.

Evidence is gathered from real ToolResult output (or, in simulation mode,
simulated ToolResult output) rather than authored curriculum content: see
troubleshooting/service.py and docs/architecture.md#troubleshooting. The
platform never asks the AI to diagnose from a one-line failure description
alone; it always assembles EvidenceItem entries first.
"""

from __future__ import annotations

from dataclasses import dataclass, field


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
