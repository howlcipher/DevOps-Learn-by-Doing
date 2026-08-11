"""Simulated DockerTool. No real docker daemon calls in V1; see docs/safety.md."""

from __future__ import annotations

from typing import Any, Mapping

from devops_learn.tools.approval import ApprovalRecord
from devops_learn.tools.base import RiskLevel, Tool, ToolOperationSpec, ToolResult

_OPERATIONS = (
    ToolOperationSpec(
        name="build",
        risk_level=RiskLevel.LOW,
        supports_dry_run=True,
        requires_approval=False,
        is_destructive=False,
    ),
    ToolOperationSpec(
        name="run",
        risk_level=RiskLevel.LOW,
        supports_dry_run=True,
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
        name="remove_image",
        risk_level=RiskLevel.HIGH,
        supports_dry_run=True,
        requires_approval=True,
        is_destructive=True,
    ),
)


class SimulatedDockerTool(Tool):
    @property
    def name(self) -> str:
        return "docker"

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
        assert not spec.requires_approval or dry_run or (approval is not None and approval.granted)

        if operation == "build":
            summary = "Successfully built image api-platform:dev (simulated)"
            details: dict[str, Any] = {"image": "api-platform:dev", "layers": 6}
        elif operation == "run":
            summary = "Container started, listening on port 8000 (simulated)"
            details = {"container_id": "sim-container-01", "port": 8000}
        elif operation == "logs":
            summary = "INFO: Uvicorn running on http://0.0.0.0:8000 (simulated)"
            details = {"lines": 1}
        else:  # remove_image
            image = params.get("image", "api-platform:dev")
            summary = f"Removed image {image} (simulated)"
            details = {"image": image}

        return ToolResult(
            success=True,
            summary=summary,
            details=details,
            risk_level=spec.risk_level,
            was_dry_run=dry_run,
            approval=approval,
        )
