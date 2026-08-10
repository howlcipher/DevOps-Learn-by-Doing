"""The only interface any tool implementation may expose.

Tool.execute is never called directly outside ToolService (see service.py):
that is what makes "destructive requires human approval" a structural
property instead of a convention every caller has to remember.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Mapping

from devops_learn.tools.approval import ApprovalRecord, RiskLevel

__all__ = ["RiskLevel", "ToolOperationSpec", "ToolResult", "Tool"]


@dataclass(frozen=True)
class ToolOperationSpec:
    name: str
    risk_level: RiskLevel
    supports_dry_run: bool
    requires_approval: bool
    is_destructive: bool

    def __post_init__(self) -> None:
        if self.risk_level is RiskLevel.DESTRUCTIVE and not self.requires_approval:
            raise ValueError(
                f"Operation '{self.name}' is DESTRUCTIVE but requires_approval=False; "
                "destructive operations must always require approval."
            )
        if self.risk_level is RiskLevel.DESTRUCTIVE and self.supports_dry_run:
            raise ValueError(
                f"Operation '{self.name}' is DESTRUCTIVE but supports_dry_run=True; "
                "a dry run must never be usable to bypass approval for a destructive action."
            )


@dataclass(frozen=True)
class ToolResult:
    success: bool
    summary: str
    details: Mapping[str, Any]
    risk_level: RiskLevel
    was_dry_run: bool
    approval: ApprovalRecord | None = None


class Tool(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def operations(self) -> tuple[ToolOperationSpec, ...]: ...

    @abstractmethod
    def execute(
        self,
        operation: str,
        params: Mapping[str, Any],
        *,
        dry_run: bool,
        approval: ApprovalRecord | None,
    ) -> ToolResult:
        """Only ToolService.invoke may call this. See service.py."""

    def spec_for(self, operation: str) -> ToolOperationSpec:
        for spec in self.operations:
            if spec.name == operation:
                return spec
        raise KeyError(f"{self.name} has no operation '{operation}'")
