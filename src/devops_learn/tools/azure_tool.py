"""A deliberately narrow, real Azure CLI boundary.

This tool is read-only except for ``acr_login``.  It never accepts arbitrary
Azure CLI arguments, never prints credentials, and makes the declaration vs.
observation distinction explicit for the deployment workflow.
"""

from __future__ import annotations

import json
import shutil
from typing import Any, Mapping

from devops_learn.tools import _subprocess_safety
from devops_learn.tools.approval import ApprovalRecord
from devops_learn.tools.base import RiskLevel, Tool, ToolOperationSpec, ToolResult

_OPERATIONS = (
    ToolOperationSpec("preflight", RiskLevel.SAFE, False, False, False),
    ToolOperationSpec("verify_environment", RiskLevel.SAFE, False, False, False),
    ToolOperationSpec("verify_cleanup", RiskLevel.SAFE, False, False, False),
    ToolOperationSpec("container_app_evidence", RiskLevel.SAFE, False, False, False),
    ToolOperationSpec("acr_login", RiskLevel.LOW, False, False, False),
)


def _az_command() -> str:
    command = shutil.which("az")
    if command is None:
        raise FileNotFoundError("Azure CLI not found. Install it, then run `az login`.")
    return command


def _json(command: list[str], *, timeout: int = 45) -> tuple[bool, dict[str, Any], str]:
    result = _subprocess_safety.run_safely(command, cwd=None, timeout=timeout)
    if result.returncode != 0:
        return False, {}, result.stderr or result.stdout
    try:
        parsed = json.loads(result.stdout)
    except json.JSONDecodeError:
        return False, {}, "Azure CLI returned malformed JSON."
    return isinstance(parsed, dict), parsed if isinstance(parsed, dict) else {}, ""


class AzureCliTool(Tool):
    @property
    def name(self) -> str:
        return "azure"

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
        if dry_run:
            return ToolResult(
                True, f"Would run Azure {operation} (dry run)", {}, spec.risk_level, True, approval
            )
        try:
            az = _az_command()
            if operation == "preflight":
                return self._preflight(az, params, spec, approval)
            if operation == "acr_login":
                registry = str(params.get("registry_name", ""))
                if not registry:
                    raise ValueError("ACR login requires a registry name.")
                result = _subprocess_safety.run_safely(
                    [az, "acr", "login", "--name", registry, "--only-show-errors"],
                    cwd=None,
                    timeout=90,
                )
                return ToolResult(
                    result.returncode == 0,
                    "(real) authenticated Docker to ACR"
                    if result.returncode == 0
                    else "(real, failed) ACR login failed",
                    {"returncode": result.returncode, "stderr": result.stderr},
                    spec.risk_level,
                    False,
                    approval,
                )
            resource_group = str(params.get("resource_group", ""))
            if not resource_group:
                raise ValueError("Azure verification requires a resource group.")
            if operation == "verify_cleanup":
                result = _subprocess_safety.run_safely(
                    [az, "group", "exists", "--name", resource_group], cwd=None, timeout=45
                )
                removed = result.returncode == 0 and result.stdout.strip().lower() == "false"
                return ToolResult(
                    removed,
                    "(real) Azure resource group is gone"
                    if removed
                    else "(real, failed) Azure resource group still exists",
                    {"resource_group": resource_group, "exists": result.stdout.strip()},
                    spec.risk_level,
                    False,
                    approval,
                )
            if operation == "container_app_evidence":
                app = str(params.get("container_app_name", ""))
                command = [
                    az,
                    "containerapp",
                    "show",
                    "--name",
                    app,
                    "--resource-group",
                    resource_group,
                    "--output",
                    "json",
                ]
                ok, payload, error = _json(command)
                safe = _container_app_view(payload)
                return ToolResult(
                    ok,
                    "(real) collected Container App evidence"
                    if ok
                    else "(real, failed) could not collect Container App evidence",
                    safe if ok else {"error": error},
                    spec.risk_level,
                    False,
                    approval,
                )
            return self._verify_environment(az, params, spec, approval)
        except (FileNotFoundError, OSError, ValueError) as exc:
            return ToolResult(
                False,
                f"(real, failed) {exc}",
                {"error": str(exc)},
                spec.risk_level,
                False,
                approval,
            )

    def _preflight(
        self,
        az: str,
        params: Mapping[str, Any],
        spec: ToolOperationSpec,
        approval: ApprovalRecord | None,
    ) -> ToolResult:
        ok, account, error = _json([az, "account", "show", "--output", "json"])
        if not ok:
            return ToolResult(
                False,
                "(real, failed) Azure authentication unavailable; run `az login`.",
                {"error": error},
                spec.risk_level,
                False,
                approval,
            )
        details = {
            "subscription": str(account.get("name", "unknown")),
            "subscription_id": str(account.get("id", "unknown")),
            "tenant": str(account.get("tenantId", "unavailable")),
            "region": str(params.get("region", "eastus")),
            "environment": str(params.get("environment", "learning")),
        }
        return ToolResult(
            True,
            "(real) Azure authentication preflight passed",
            details,
            spec.risk_level,
            False,
            approval,
        )

    def _verify_environment(
        self,
        az: str,
        params: Mapping[str, Any],
        spec: ToolOperationSpec,
        approval: ApprovalRecord | None,
    ) -> ToolResult:
        group = str(params["resource_group"])
        commands = {
            "resource_group": [az, "group", "show", "--name", group, "--output", "json"],
            "acr": [
                az,
                "acr",
                "show",
                "--name",
                str(params["acr_name"]),
                "--resource-group",
                group,
                "--output",
                "json",
            ],
            "environment": [
                az,
                "containerapp",
                "env",
                "show",
                "--name",
                str(params["container_environment_name"]),
                "--resource-group",
                group,
                "--output",
                "json",
            ],
            "container_app": [
                az,
                "containerapp",
                "show",
                "--name",
                str(params["container_app_name"]),
                "--resource-group",
                group,
                "--output",
                "json",
            ],
        }
        observed: dict[str, Any] = {}
        for name, command in commands.items():
            ok, payload, error = _json(command)
            if not ok:
                return ToolResult(
                    False,
                    f"(real, failed) Azure did not verify {name}",
                    {"error": error, "observed": observed},
                    spec.risk_level,
                    False,
                    approval,
                )
            observed[name] = (
                _container_app_view(payload) if name == "container_app" else _resource_view(payload)
            )
        expected_region = str(params.get("expected_region", "")).lower()
        actual_region = str(observed["resource_group"].get("location", "")).lower()
        expected_tags = params.get("expected_tags", {})
        actual_tags = observed["resource_group"].get("tags", {})
        valid = (not expected_region or expected_region == actual_region) and all(
            actual_tags.get(k) == v for k, v in expected_tags.items()
        )
        return ToolResult(
            valid,
            "(real) DECLARED BY TERRAFORM matches OBSERVED IN AZURE"
            if valid
            else "(real, failed) Azure observation does not match declared region or tags",
            observed,
            spec.risk_level,
            False,
            approval,
        )


def _resource_view(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": payload.get("id"),
        "name": payload.get("name"),
        "location": payload.get("location"),
        "tags": payload.get("tags", {}),
    }


def _container_app_view(payload: dict[str, Any]) -> dict[str, Any]:
    properties = payload.get("properties", {})
    template = properties.get("template", {})
    containers = template.get("containers", [])
    ingress = properties.get("configuration", {}).get("ingress", {})
    return {
        "name": payload.get("name"),
        "location": payload.get("location"),
        "tags": payload.get("tags", {}),
        "image": containers[0].get("image") if containers else None,
        "endpoint": ingress.get("fqdn"),
        "revision": properties.get("latestRevisionName"),
        "running_status": properties.get("runningStatus"),
    }
