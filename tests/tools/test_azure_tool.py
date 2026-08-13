from typing import Any, Mapping

from devops_learn.tools.approval import (
    ApprovalRecord,
    AutoApproveApprovalGate,
    AutoDenyApprovalGate,
)
from devops_learn.tools import azure_tool
from devops_learn.tools.azure_tool import AzureCliTool, _container_app_view
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
        "endpoint": "https://api.example.invalid",
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


def test_azure_verification_rejects_a_different_deployed_image(monkeypatch) -> None:
    payloads = {
        "group": {"name": "rg", "location": "eastus", "tags": {"environment": "learning"}},
        "acr": {"name": "acr", "location": "eastus", "tags": {"environment": "learning"}},
        "env": {"name": "env", "location": "eastus", "tags": {"environment": "learning"}},
        "app": {
            "name": "app",
            "location": "eastus",
            "tags": {"environment": "learning"},
            "properties": {
                "configuration": {"ingress": {"fqdn": "app.example.invalid"}},
                "template": {"containers": [{"image": "acr/api@sha256:old"}]},
            },
        },
    }

    def fake_json(command: list[str], *, timeout: int = 45):
        if command[1:3] == ["group", "show"]:
            return True, payloads["group"], ""
        if command[1:3] == ["acr", "show"]:
            return True, payloads["acr"], ""
        if command[1:4] == ["containerapp", "env", "show"]:
            return True, payloads["env"], ""
        return True, payloads["app"], ""

    monkeypatch.setattr(azure_tool, "_az_command", lambda: "az")
    monkeypatch.setattr(azure_tool, "_json", fake_json)
    result = AzureCliTool().execute(
        "verify_environment",
        {
            "resource_group": "rg",
            "acr_name": "acr",
            "container_environment_name": "env",
            "container_app_name": "app",
            "expected_region": "eastus",
            "expected_tags": {"environment": "learning"},
            "expected_image": "acr/api@sha256:new",
        },
        dry_run=False,
        approval=None,
    )
    assert not result.success
    assert result.details["container_app"]["endpoint"] == "https://app.example.invalid"


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
