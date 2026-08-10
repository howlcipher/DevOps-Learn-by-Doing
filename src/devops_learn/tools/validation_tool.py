"""Simulated ValidationTool: lightweight checks reused across lessons."""

from __future__ import annotations

from typing import Any, Mapping

from devops_learn.tools.approval import ApprovalRecord
from devops_learn.tools.base import (
    RiskLevel,
    Tool,
    ToolOperationSpec,
    ToolResult,
    ensure_approved,
)

_OPERATIONS = (
    ToolOperationSpec(
        name="check_dockerfile_best_practices",
        risk_level=RiskLevel.SAFE,
        supports_dry_run=False,
        requires_approval=False,
        is_destructive=False,
    ),
    ToolOperationSpec(
        name="check_yaml_syntax",
        risk_level=RiskLevel.SAFE,
        supports_dry_run=False,
        requires_approval=False,
        is_destructive=False,
    ),
)


class SimulatedValidationTool(Tool):
    @property
    def name(self) -> str:
        return "validation"

    @property
    def operations(self) -> tuple[ToolOperationSpec, ...]:
        return _OPERATIONS

    def execute(
        self,
        operation: str,
        params: Mapping[str, Any],
        *,
        dry_run: bool,
        approval: ApprovalRecord | None,
    ) -> ToolResult:
        spec = self.spec_for(operation)
        ensure_approved(self.name, spec, dry_run=dry_run, approval=approval)

        if operation == "check_dockerfile_best_practices":
            summary = "No issues found: base image pinned, non-root user present (simulated)"
            details: dict[str, Any] = {"issues": []}
        else:  # check_yaml_syntax
            summary = "YAML is well-formed (simulated)"
            details = {"valid": True}

        return ToolResult(
            success=True,
            summary=summary,
            details=details,
            risk_level=spec.risk_level,
            was_dry_run=dry_run,
            approval=approval,
        )
