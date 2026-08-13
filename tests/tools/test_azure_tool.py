from typing import Any, Mapping

from devops_learn.tools.approval import (
    ApprovalRecord,
    AutoApproveApprovalGate,
    AutoDenyApprovalGate,
)
from devops_learn.tools.azure_tool import _container_app_view
from devops_learn.tools.base import RiskLevel, Tool, ToolOperationSpec, ToolResult
from devops_learn.tools.service import ToolService


def test_container_app_observation_is_sanitized_to_deployment_facts() -> None:
    observed = _container_app_view(
        {
            "name": "api",
            "location": "eastus",
            "tags": {"environment": "learning"},
            "properties": {
                "latestRevisionName": "api--one",
                "runningStatus": "Running",
                "configuration": {"ingress": {"fqdn": "api.example.invalid"}},
                "template": {"containers": [{"image": "acr.azurecr.io/api@sha256:abc"}]},
            },
        }
    )
    assert observed == {
        "name": "api",
        "location": "eastus",
        "tags": {"environment": "learning"},
        "image": "acr.azurecr.io/api@sha256:abc",
        "endpoint": "api.example.invalid",
        "revision": "api--one",
        "running_status": "Running",
    }


def test_destroy_operation_requires_toolservice_approval() -> None:
    denied = ToolService({"terraform": _DestroySpy()}, AutoDenyApprovalGate()).invoke(
        "terraform", "destroy_approved_environment", {"environment": "learning"}
    )
    assert not denied.success
    approved = ToolService({"terraform": _DestroySpy()}, AutoApproveApprovalGate()).invoke(
        "terraform", "destroy_approved_environment", {"environment": "learning"}
    )
    assert approved.success


class _DestroySpy(Tool):
    @property
    def name(self) -> str:
        return "terraform"

    @property
    def operations(self) -> tuple[ToolOperationSpec, ...]:
        return (
            ToolOperationSpec(
                "destroy_approved_environment", RiskLevel.DESTRUCTIVE, False, True, True
            ),
        )

    def execute(
        self,
        operation: str,
        params: Mapping[str, Any],
        *,
        dry_run: bool,
        approval: ApprovalRecord | None,
    ) -> ToolResult:
        return ToolResult(True, "destroyed", {}, RiskLevel.DESTRUCTIVE, dry_run, approval)
