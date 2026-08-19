"""Base interface for troubleshooting scenario handlers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from devops_learn.domain.troubleshooting_models import (
    Observation,
    RemediationAttempt,
    TroubleshootingScenario,
    VerificationResult,
)
from devops_learn.tools.service import ToolService


@dataclass
class ScenarioContext:
    scenario: TroubleshootingScenario
    is_live: bool
    project_root: str
    tool_service: ToolService
    state: dict[str, Any] = field(default_factory=dict)


class ScenarioHandler(ABC):
    @property
    @abstractmethod
    def definition(self) -> TroubleshootingScenario:
        """The declarative specification of this troubleshooting scenario."""

    @abstractmethod
    def setup_and_inject(self, context: ScenarioContext) -> tuple[Observation, ...]:
        """Perform setup, safely inject the fault, and return baseline observations."""

    @abstractmethod
    def remediate(
        self, context: ScenarioContext, attempt: RemediationAttempt
    ) -> tuple[Observation, ...]:
        """Apply the remediation attempt and return intermediate observations."""

    @abstractmethod
    def verify(
        self, context: ScenarioContext, attempt: RemediationAttempt
    ) -> VerificationResult:
        """Deterministically verify if recovery was achieved."""

    @abstractmethod
    def cleanup(self, context: ScenarioContext) -> None:
        """Guaranteed cleanup of temporary resources, sockets, or containers."""
