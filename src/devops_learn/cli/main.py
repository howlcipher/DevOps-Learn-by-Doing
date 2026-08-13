"""Entry point: `devops-learn <command>`. See docs/adr/0001-cli-first.md."""

from __future__ import annotations

import argparse
from typing import Sequence

from devops_learn.ai.anthropic_provider import AnthropicProvider
from devops_learn.bootstrap import build_platform
from devops_learn.cli.commands import (
    analyze,
    deploy,
    destroy,
    explain,
    history,
    init,
    local,
    profile,
    review,
    security,
    terraform,
)
from devops_learn.config.settings import load_settings
from devops_learn.domain.enums import ExecutionMode
from devops_learn.learning.persistence.connection import connect
from devops_learn.tools.approval import ApprovalGate, CliApprovalGate, ThresholdApprovalGate
from devops_learn.tools.base import RiskLevel, Tool
from devops_learn.tools.docker_tool import RealDockerTool, SimulatedDockerTool
from devops_learn.tools.git_tool import SimulatedGitTool
from devops_learn.tools.kubernetes_tool import SimulatedKubernetesTool
from devops_learn.tools.python_tool import RealPythonTool, SimulatedPythonTool
from devops_learn.tools.terraform_tool import RealTerraformTool, SimulatedTerraformTool
from devops_learn.tools.validation_tool import SimulatedValidationTool
from devops_learn.tools.cloud_tool import SimulatedCloudTool
from devops_learn.tools.policy_tool import PolicyTool
from devops_learn.tools.security_scanner_tool import SecurityScannerTool
from devops_learn.tools.azure_tool import AzureCliTool

_COMMAND_MODULES = (
    analyze,
    review,
    history,
    explain,
    profile,
    init,
    local,
    terraform,
    security,
    deploy,
    destroy,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="devops-learn",
        description=(
            "AI-powered, explainable DevOps platform: assess a project, recommend and explain "
            "an architecture, build it with human approval, and validate the result."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    for module in _COMMAND_MODULES:
        module.register(subparsers)
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    settings = load_settings()
    conn = connect(settings.db_path)
    try:
        llm_provider = (
            AnthropicProvider(api_key=settings.anthropic_api_key)
            if settings.anthropic_api_key
            else None
        )
        approval_gate = _approval_gate_for_args(args)
        tools = _tools_for_args(args)
        platform = build_platform(
            conn, llm_provider=llm_provider, approval_gate=approval_gate, tools=tools
        )
        args.handler(args, platform)
    finally:
        conn.close()


def _approval_gate_for_args(args: argparse.Namespace) -> ApprovalGate:
    base_gate = CliApprovalGate()
    mode_value = getattr(args, "mode", None)
    if mode_value == ExecutionMode.GUIDED.value:
        return ThresholdApprovalGate(base_gate, RiskLevel.LOW)
    return base_gate


def _tools_for_args(args: argparse.Namespace) -> dict[str, Tool] | None:
    if args.command == "security":
        return {"security_scanner": SecurityScannerTool(), "security_policy": PolicyTool()}
    if args.command == "terraform":
        # This command only ever invokes the "terraform" tool -- keep the rest
        # simulated rather than provisioning real python/docker tools it never uses.
        return {
            "python": SimulatedPythonTool(),
            "git": SimulatedGitTool(),
            "docker": SimulatedDockerTool(),
            "terraform": RealTerraformTool(),
            "kubernetes": SimulatedKubernetesTool(),
            "cloud": SimulatedCloudTool(),
            "validation": SimulatedValidationTool(),
        }
    if args.command in {"deploy", "destroy"}:
        return {
            "python": RealPythonTool(),
            "git": SimulatedGitTool(),
            "docker": RealDockerTool(),
            "terraform": RealTerraformTool(),
            "kubernetes": SimulatedKubernetesTool(),
            "cloud": SimulatedCloudTool(),
            "validation": SimulatedValidationTool(),
            "security_scanner": SecurityScannerTool(),
            "security_policy": PolicyTool(),
            "azure": AzureCliTool(),
        }
    if getattr(args, "real_tools", False) or args.command == "local":
        return {
            "python": RealPythonTool(),
            "git": SimulatedGitTool(),
            "docker": RealDockerTool(),
            "terraform": SimulatedTerraformTool(),
            "kubernetes": SimulatedKubernetesTool(),
            "cloud": SimulatedCloudTool(),
            "validation": SimulatedValidationTool(),
        }
    return None


if __name__ == "__main__":
    main()
