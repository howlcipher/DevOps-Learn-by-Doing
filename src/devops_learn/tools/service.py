"""The sole entry point for invoking any tool. See docs/safety.md.

Tool.execute is never called from anywhere else, which is what makes
"destructive operations require human approval" structural rather than a
convention every caller has to remember to follow.
"""

from __future__ import annotations

from typing import Any, Mapping

from devops_learn.tools.approval import ApprovalGate
from devops_learn.tools.base import Tool, ToolResult


class UnknownToolError(Exception):
    pass


class ToolService:
    def __init__(self, tools: dict[str, Tool], approval_gate: ApprovalGate) -> None:
        self._tools = tools
        self._approval_gate = approval_gate

    def invoke(
        self,
        tool_name: str,
        operation: str,
        params: Mapping[str, Any] | None = None,
        *,
        dry_run: bool = False,
    ) -> ToolResult:
        if tool_name not in self._tools:
            raise UnknownToolError(f"Unknown tool '{tool_name}'")
        tool = self._tools[tool_name]
        spec = tool.spec_for(operation)
        params = params or {}

        if dry_run and not spec.supports_dry_run:
            raise ValueError(f"'{tool_name}.{operation}' does not support dry_run")

        approval = None
        if spec.requires_approval and not dry_run:
            approval = self._approval_gate.request(spec.name, spec.risk_level, params)
            if not approval.granted:
                return ToolResult(
                    success=False,
                    summary=f"Approval denied for {tool_name}.{operation}",
                    details={},
                    risk_level=spec.risk_level,
                    was_dry_run=dry_run,
                    approval=approval,
                )

        return tool.execute(operation, params, dry_run=dry_run, approval=approval)
