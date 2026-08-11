"""Implementation plan steps and Terraform plan risk analysis.

PlanStep names a controlled Tool operation (tools/base.py) rather than free
text, so PlanningService output can be executed directly by ToolService
without a second translation layer; see docs/adr/0004.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from devops_learn.domain.enums import ChangeAction
from devops_learn.tools.approval import RiskLevel


@dataclass(frozen=True)
class PlanStep:
    id: str
    title: str
    tool_name: str
    operation: str
    risk_level: RiskLevel
    requires_approval: bool
    params: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class ImplementationPlan:
    steps: tuple[PlanStep, ...]


@dataclass(frozen=True)
class ResourceChange:
    resource: str
    action: ChangeAction


@dataclass(frozen=True)
class TerraformPlanSummary:
    changes: tuple[ResourceChange, ...]
    risk_level: RiskLevel
    reason: str

    def count(self, action: ChangeAction) -> int:
        return sum(1 for change in self.changes if change.action is action)
