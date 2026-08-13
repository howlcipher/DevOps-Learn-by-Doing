"""`devops-learn security`: doctor and evidence-backed security scanning."""

from __future__ import annotations

import argparse

from devops_learn.bootstrap import Platform
from devops_learn.cli.terminal_ui import TerminalUi
from devops_learn.domain.enums import SecurityGateDecision
from devops_learn.workflows.security_flow import (
    SecurityOptions,
    run_security_doctor,
    run_security_scan,
)


def register(subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
    parser = subparsers.add_parser(
        "security", help="Run DevSecOps evidence, policy, and gate checks"
    )
    commands = parser.add_subparsers(dest="security_command", required=True)
    doctor = commands.add_parser("doctor", help="Report security scanner prerequisites")
    doctor.set_defaults(handler=run_doctor)
    scan = commands.add_parser(
        "scan", help="Scan filesystem/config, compare a Git base, and evaluate policy"
    )
    scan.add_argument(
        "path", nargs="?", default=".", help="Git repository or project directory to scan"
    )
    scan.add_argument("--base-ref", help="Comparable Git base ref, such as origin/main")
    scan.add_argument("--image", help="Optional already-built Docker image to scan with Trivy")
    scan.add_argument("--report", help="Path for the sanitized JSON report")
    scan.set_defaults(handler=run_scan)


def run_doctor(args: argparse.Namespace, platform: Platform) -> None:
    run_security_doctor(platform, TerminalUi())


def run_scan(args: argparse.Namespace, platform: Platform) -> None:
    report = run_security_scan(
        platform, TerminalUi(), SecurityOptions(args.path, args.base_ref, args.image, args.report)
    )
    if report and report.policy.decision is SecurityGateDecision.BLOCK:
        raise SystemExit(2)
