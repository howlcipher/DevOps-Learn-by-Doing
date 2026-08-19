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
    doctor,
    explain,
    history,
    init,
    local,
    profile,
    report,
    review,
    security,
    terraform,
    ai_test,
    config,
    troubleshoot,
)
from devops_learn.config.settings import load_settings
from devops_learn.domain.enums import ExecutionMode
from devops_learn.learning.persistence.connection import connect
from devops_learn.tools.approval import (
    ApprovalGate,
    CliApprovalGate,
    ThresholdApprovalGate,
)
from devops_learn.tools.base import RiskLevel, Tool
from devops_learn.tools.docker_tool import RealDockerTool, SimulatedDockerTool
from devops_learn.tools.doctor_tool import EnvironmentDoctorTool
from devops_learn.tools.git_tool import SimulatedGitTool
from devops_learn.tools.go_tool import RealGoTool, SimulatedGoTool
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
    doctor,
    report,
    ai_test,
    config,
    troubleshoot,
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


def _show_first_run_screen() -> None:
    import os
    import sys
    from devops_learn.config.settings import load_settings
    from devops_learn.bootstrap import build_platform
    from devops_learn.learning.persistence.connection import connect
    from devops_learn.workflows.doctor_flow import collect_doctor_report
    from devops_learn.tools.doctor_tool import EnvironmentDoctorTool
    from devops_learn.tools.security_scanner_tool import SecurityScannerTool
    from devops_learn.tools.policy_tool import PolicyTool

    def _c(text: str, code: str) -> str:
        if (
            not sys.stdout.isatty()
            or os.environ.get("NO_COLOR")
            or os.environ.get("TERM") == "dumb"
        ):
            return text
        return f"\033[{code}m{text}\033[0m"

    print(_c("DEVOPS LEARN", "1"))
    print("\nAI-assisted DevOps mastery through real engineering.\n")

    settings = load_settings()
    conn = connect(settings.db_path)
    try:
        platform = build_platform(
            conn,
            llm_provider=None,
            approval_gate=CliApprovalGate(),
            tools={
                "doctor": EnvironmentDoctorTool(),
                "security_scanner": SecurityScannerTool(),
                "security_policy": PolicyTool(),
            },
        )
        report = collect_doctor_report(platform)

        print(_c("READY", "1"))
        print(
            f"{'Local environment':<23} {'YES' if report.local_workflow_ready else 'NO'}"
        )
        print(
            f"{'Security tooling':<23} {'YES' if report.security_workflow_ready else 'NO'}"
        )
        print(f"{'Terraform':<23} {'YES' if report.terraform_planning_ready else 'NO'}")
        print(f"{'Azure':<23} {'YES' if report.azure_deployment_ready else 'NO'}")
        profile = platform.learner_profile_service.load()
        has_profile = bool(profile.proficiencies or profile.learning_focus)
        print(f"{'Learner profile':<23} {'YES' if has_profile else 'NO'}")
        print("\n" + _c("NEXT", "1"))

        if not report.local_workflow_ready or not report.security_workflow_ready:
            print("devops-learn doctor")
        else:
            print("devops-learn init <project>")
    finally:
        conn.close()


def main(argv: Sequence[str] | None = None) -> None:
    import sys

    effective_argv = sys.argv[1:] if argv is None else argv
    if not effective_argv:
        _show_first_run_screen()
        return

    parser = build_parser()
    args = parser.parse_args(effective_argv)

    settings = load_settings()
    conn = connect(settings.db_path)
    try:
        if settings.ai_provider == "anthropic" or (
            settings.ai_provider == "auto" and settings.anthropic_api_key
        ):
            llm_provider = AnthropicProvider(api_key=settings.anthropic_api_key)
        else:
            llm_provider = None

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
    if args.command in {"doctor", "init"}:
        return {
            "doctor": EnvironmentDoctorTool(),
            "security_scanner": SecurityScannerTool(),
            "security_policy": PolicyTool(),
        }
    if args.command == "security":
        return {
            "security_scanner": SecurityScannerTool(),
            "security_policy": PolicyTool(),
        }
    if args.command == "terraform":
        # This command only ever invokes the "terraform" tool -- keep the rest
        # simulated rather than provisioning real python/docker tools it never uses.
        return {
            "python": SimulatedPythonTool(),
            "go": SimulatedGoTool(),
            "git": SimulatedGitTool(),
            "docker": SimulatedDockerTool(),
            "terraform": RealTerraformTool(),
            "kubernetes": SimulatedKubernetesTool(),
            "cloud": SimulatedCloudTool(),
            "validation": SimulatedValidationTool(),
        }
    if args.command in {"deploy", "destroy"}:
        return {
            "doctor": EnvironmentDoctorTool(),
            "python": RealPythonTool(),
            "go": RealGoTool(),
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
    is_troubleshoot_real = args.command == "troubleshoot" and getattr(args, "real", False)
    if getattr(args, "real_tools", False) or args.command == "local" or is_troubleshoot_real:
        return {
            "python": RealPythonTool(),
            "go": RealGoTool(),
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
