"""Capability-specific local preflight for real platform workflows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from devops_learn.bootstrap import Platform
from devops_learn.workflows.ui import Ui


@dataclass(frozen=True)
class DoctorCheck:
    label: str
    available: bool
    detail: str = ""


@dataclass(frozen=True)
class DoctorReport:
    checks: tuple[DoctorCheck, ...]
    local_workflow_ready: bool
    security_workflow_ready: bool
    terraform_planning_ready: bool
    azure_deployment_ready: bool


_CHECKS = (
    ("python", "Python"),
    ("git", "Git"),
    ("docker", "Docker"),
    ("docker_daemon", "Docker daemon"),
    ("terraform", "Terraform"),
    ("azure_cli", "Azure CLI"),
    ("azure_auth", "Azure auth"),
    ("trivy", "Trivy"),
    ("conftest", "Conftest"),
)


def _available(details: Mapping[str, Any], name: str) -> bool:
    return bool(details.get(name, {}).get("available", False))


def collect_doctor_report(platform: Platform) -> DoctorReport:
    environment = platform.tool_service.invoke("doctor", "check", {}).details.get("checks", {})
    if not isinstance(environment, Mapping):
        environment = {}
    trivy = platform.tool_service.invoke("security_scanner", "version")
    conftest = platform.tool_service.invoke("security_policy", "version")
    checks: dict[str, Mapping[str, Any]] = dict(environment)
    checks["trivy"] = {
        "available": trivy.success,
        "version": trivy.summary.removeprefix("(real) ").removeprefix("(real, failed) "),
    }
    checks["conftest"] = {
        "available": conftest.success,
        "version": conftest.summary.removeprefix("(real) ").removeprefix("(real, failed) "),
    }
    rendered = tuple(
        DoctorCheck(
            label,
            _available(checks, key),
            str(checks.get(key, {}).get("version", "not found")),
        )
        for key, label in _CHECKS
    )
    ready = {key: _available(checks, key) for key, _ in _CHECKS}
    return DoctorReport(
        checks=rendered,
        local_workflow_ready=ready["python"] and ready["docker"] and ready["docker_daemon"],
        security_workflow_ready=ready["git"] and ready["trivy"] and ready["conftest"],
        terraform_planning_ready=ready["terraform"] and ready["azure_cli"] and ready["azure_auth"],
        azure_deployment_ready=all(ready.values()),
    )


def render_doctor_report(report: DoctorReport) -> str:
    lines = ["DEVOPS-LEARN DOCTOR", ""]
    for check in report.checks:
        status = "PASS" if check.available else "FAIL"
        detail = f"  {check.detail}" if check.detail else ""
        lines.append(f"{check.label:<14} {status}{detail}")
    lines.extend(
        (
            "",
            "READY FOR:",
            f"Local workflow:     {'YES' if report.local_workflow_ready else 'NO'}",
            f"Security workflow:  {'YES' if report.security_workflow_ready else 'NO'}",
            f"Terraform planning: {'YES' if report.terraform_planning_ready else 'NO'}",
            f"Azure deployment:   {'YES' if report.azure_deployment_ready else 'NO'}",
        )
    )
    actions: list[str] = []
    unavailable = {check.label for check in report.checks if not check.available}
    if "Docker" in unavailable:
        actions.append("Install Docker, then rerun `devops-learn doctor`.")
    elif "Docker daemon" in unavailable:
        actions.append("Start Docker, then rerun `devops-learn doctor`.")
    if "Azure CLI" in unavailable:
        actions.append("Install the Azure CLI, then rerun `devops-learn doctor`.")
    elif "Azure auth" in unavailable:
        actions.append("Authenticate Azure using `az login`.")
    if "Trivy" in unavailable:
        actions.append("Install Trivy for the security workflow.")
    if "Conftest" in unavailable:
        actions.append("Install Conftest for the security workflow.")
    if actions:
        lines.extend(("", "ACTION REQUIRED:", *actions))
    return "\n".join(lines)


def run_doctor(platform: Platform, ui: Ui) -> DoctorReport:
    report = collect_doctor_report(platform)
    ui.present(render_doctor_report(report))
    return report
