"""Safe, bounded checks for the local DevOps learning environment."""

from __future__ import annotations

import json
import shutil
import sys
from typing import Any, Mapping

from devops_learn.tools import _subprocess_safety
from devops_learn.tools.approval import ApprovalRecord
from devops_learn.tools.base import RiskLevel, Tool, ToolOperationSpec, ToolResult

_OPERATIONS = (ToolOperationSpec("check", RiskLevel.SAFE, False, False, False),)


def _first_line(value: str) -> str:
    return next((line.strip() for line in value.splitlines() if line.strip()), "available")


def _binary_check(command: str, arguments: list[str]) -> dict[str, object]:
    binary = shutil.which(command)
    if binary is None:
        return {"available": False, "version": "not found"}
    result = _subprocess_safety.run_safely([binary, *arguments], cwd=None, timeout=15)
    return {
        "available": result.returncode == 0,
        "version": _first_line(result.stdout or result.stderr),
    }


def _azure_authentication() -> bool:
    az = shutil.which("az")
    if az is None:
        return False
    result = _subprocess_safety.run_safely(
        [az, "account", "show", "--output", "json", "--only-show-errors"],
        cwd=None,
        timeout=20,
    )
    if result.returncode != 0:
        return False
    try:
        account = json.loads(result.stdout)
    except json.JSONDecodeError:
        return False
    return isinstance(account, dict) and bool(account.get("id")) and bool(account.get("tenantId"))


class EnvironmentDoctorTool(Tool):
    """Checks command availability without installing, authenticating, or changing state."""

    @property
    def name(self) -> str:
        return "doctor"

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
                True, "Would inspect environment (dry run)", {}, spec.risk_level, True
            )

        docker = _binary_check("docker", ["--version"])
        docker_daemon = (
            _binary_check("docker", ["info", "--format", "{{.ServerVersion}}"])
            if docker["available"]
            else {"available": False, "version": "Docker CLI unavailable"}
        )
        azure = _binary_check("az", ["version", "--output", "json", "--only-show-errors"])
        checks = {
            "python": {
                "available": sys.version_info >= (3, 11),
                "version": ".".join(str(item) for item in sys.version_info[:3]),
            },
            "git": _binary_check("git", ["--version"]),
            "docker": docker,
            "docker_daemon": docker_daemon,
            "terraform": _binary_check("terraform", ["version"]),
            "azure_cli": azure,
            "azure_auth": {"available": bool(azure["available"]) and _azure_authentication()},
        }
        return ToolResult(
            True,
            "(real) environment checks completed",
            {"checks": checks},
            spec.risk_level,
            False,
            approval,
        )
