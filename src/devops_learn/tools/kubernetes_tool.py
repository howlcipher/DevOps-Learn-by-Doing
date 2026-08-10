"""Simulated KubernetesTool. No real kubectl invoked in V1; see docs/safety.md."""

from __future__ import annotations

from typing import Any, Mapping

from devops_learn.tools.approval import ApprovalRecord
from devops_learn.tools.base import RiskLevel, Tool, ToolOperationSpec, ToolResult

_OPERATIONS = (
    ToolOperationSpec(
        name="get_pods",
        risk_level=RiskLevel.SAFE,
        supports_dry_run=False,
        requires_approval=False,
        is_destructive=False,
    ),
    ToolOperationSpec(
        name="describe",
        risk_level=RiskLevel.SAFE,
        supports_dry_run=False,
        requires_approval=False,
        is_destructive=False,
    ),
    ToolOperationSpec(
        name="logs",
        risk_level=RiskLevel.SAFE,
        supports_dry_run=False,
        requires_approval=False,
        is_destructive=False,
    ),
    ToolOperationSpec(
        name="rollout_status",
        risk_level=RiskLevel.SAFE,
        supports_dry_run=False,
        requires_approval=False,
        is_destructive=False,
    ),
    ToolOperationSpec(
        name="rollback",
        risk_level=RiskLevel.HIGH,
        supports_dry_run=True,
        requires_approval=True,
        is_destructive=False,
    ),
    ToolOperationSpec(
        name="delete_namespace",
        risk_level=RiskLevel.DESTRUCTIVE,
        supports_dry_run=False,
        requires_approval=True,
        is_destructive=True,
    ),
)


class SimulatedKubernetesTool(Tool):
    @property
    def name(self) -> str:
        return "kubernetes"

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

        details: dict[str, Any] = {}
        if operation == "get_pods":
            summary = "api-platform-7f9c8-abcde   1/1   Running   0   2m (simulated)"
            details = {"ready": 1, "total": 1}
        elif operation == "describe":
            summary = "Events: Scheduled, Pulled, Created, Started (simulated)"
        elif operation == "logs":
            summary = "INFO: Uvicorn running on http://0.0.0.0:8000 (simulated)"
        elif operation == "rollout_status":
            summary = "deployment \"api-platform\" successfully rolled out (simulated)"
        elif operation == "rollback":
            summary = "Rolled back to revision 1 (simulated)"
            details = {"revision": 1}
        else:  # delete_namespace
            namespace = params.get("namespace", "api-platform")
            summary = f"namespace \"{namespace}\" deleted (simulated)"
            details = {"namespace": namespace}

        return ToolResult(
            success=True,
            summary=summary,
            details=details,
            risk_level=spec.risk_level,
            was_dry_run=dry_run,
            approval=approval,
        )
