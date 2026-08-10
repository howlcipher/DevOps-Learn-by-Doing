"""Simulated PythonTool. No subprocess execution in V1; see docs/safety.md."""

from __future__ import annotations

from typing import Any, Mapping

from devops_learn.tools.approval import ApprovalRecord
from devops_learn.tools.base import RiskLevel, Tool, ToolOperationSpec, ToolResult

_OPERATIONS = (
    ToolOperationSpec(
        name="run_tests",
        risk_level=RiskLevel.SAFE,
        supports_dry_run=False,
        requires_approval=False,
        is_destructive=False,
    ),
    ToolOperationSpec(
        name="run_lint",
        risk_level=RiskLevel.SAFE,
        supports_dry_run=False,
        requires_approval=False,
        is_destructive=False,
    ),
)


class SimulatedPythonTool(Tool):
    @property
    def name(self) -> str:
        return "python"

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
        assert (
            not spec.requires_approval
            or dry_run
            or (approval is not None and approval.granted)
        )

        if operation == "run_tests":
            summary = "3 passed in 0.04s (simulated)"
            details: dict[str, Any] = {"passed": 3, "failed": 0}
        else:  # run_lint
            summary = "No lint issues found (simulated)"
            details = {"issues": 0}

        return ToolResult(
            success=True,
            summary=summary,
            details=details,
            risk_level=spec.risk_level,
            was_dry_run=dry_run,
            approval=approval,
        )
