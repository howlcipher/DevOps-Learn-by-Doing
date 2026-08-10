"""Simulated GitTool. Even objectively safe ops like status stay simulated in V1
for a clean, unambiguous boundary; see docs/adr/0003-simulation-first.md."""

from __future__ import annotations

from typing import Any, Mapping

from devops_learn.tools.approval import ApprovalRecord
from devops_learn.tools.base import RiskLevel, Tool, ToolOperationSpec, ToolResult

_OPERATIONS = (
    ToolOperationSpec(
        name="status",
        risk_level=RiskLevel.SAFE,
        supports_dry_run=False,
        requires_approval=False,
        is_destructive=False,
    ),
    ToolOperationSpec(
        name="diff",
        risk_level=RiskLevel.SAFE,
        supports_dry_run=False,
        requires_approval=False,
        is_destructive=False,
    ),
    ToolOperationSpec(
        name="log",
        risk_level=RiskLevel.SAFE,
        supports_dry_run=False,
        requires_approval=False,
        is_destructive=False,
    ),
    ToolOperationSpec(
        name="commit",
        risk_level=RiskLevel.LOW,
        supports_dry_run=True,
        requires_approval=False,
        is_destructive=False,
    ),
)


class SimulatedGitTool(Tool):
    @property
    def name(self) -> str:
        return "git"

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

        if operation == "status":
            summary = "On branch main. Changes not staged: Dockerfile (simulated)"
            details: dict[str, Any] = {"modified": ["Dockerfile"]}
        elif operation == "diff":
            summary = "diff --git a/Dockerfile b/Dockerfile (simulated)"
            details = {"files_changed": 1}
        elif operation == "log":
            summary = "1 commit on main (simulated)"
            details = {"commit_count": 1}
        else:  # commit
            message = params.get("message", "update")
            if dry_run:
                summary = f"Would commit with message: '{message}' (simulated, dry run)"
            else:
                summary = f"Committed: '{message}' (simulated)"
            details = {"message": message}

        return ToolResult(
            success=True,
            summary=summary,
            details=details,
            risk_level=spec.risk_level,
            was_dry_run=dry_run,
            approval=approval,
        )
