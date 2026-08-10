"""Simulated CloudTool. No real Azure/AWS/GCP API calls in V1; see docs/safety.md.

remove_identity and delete_resource_group are the concrete stand-ins for the
spec's "identity removal" and destructive resource examples.
"""

from __future__ import annotations

from typing import Any, Mapping

from devops_learn.tools.approval import ApprovalRecord
from devops_learn.tools.base import RiskLevel, Tool, ToolOperationSpec, ToolResult

_OPERATIONS = (
    ToolOperationSpec(
        name="list_resources",
        risk_level=RiskLevel.SAFE,
        supports_dry_run=False,
        requires_approval=False,
        is_destructive=False,
    ),
    ToolOperationSpec(
        name="estimate_cost",
        risk_level=RiskLevel.SAFE,
        supports_dry_run=False,
        requires_approval=False,
        is_destructive=False,
    ),
    ToolOperationSpec(
        name="remove_identity",
        risk_level=RiskLevel.DESTRUCTIVE,
        supports_dry_run=False,
        requires_approval=True,
        is_destructive=True,
    ),
    ToolOperationSpec(
        name="delete_resource_group",
        risk_level=RiskLevel.DESTRUCTIVE,
        supports_dry_run=False,
        requires_approval=True,
        is_destructive=True,
    ),
)


class SimulatedCloudTool(Tool):
    @property
    def name(self) -> str:
        return "cloud"

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
        if operation == "list_resources":
            summary = "0 resources found (simulation mode never creates real cloud state)"
            details = {"resources": []}
        elif operation == "estimate_cost":
            summary = (
                "Estimated cost cannot be computed precisely; simulation mode creates no "
                "billable resources"
            )
        elif operation == "remove_identity":
            identity = params.get("identity", "workload-identity")
            summary = f"Removed identity {identity} (simulated)"
            details = {"identity": identity}
        else:  # delete_resource_group
            group = params.get("resource_group", "api-platform-rg")
            summary = f"Deleted resource group {group} (simulated)"
            details = {"resource_group": group}

        return ToolResult(
            success=True,
            summary=summary,
            details=details,
            risk_level=spec.risk_level,
            was_dry_run=dry_run,
            approval=approval,
        )
