"""`devops-learn doctor`: one safe preflight for real workflows."""

from __future__ import annotations

import argparse

from devops_learn.bootstrap import Platform
from devops_learn.cli.terminal_ui import TerminalUi
from devops_learn.workflows.doctor_flow import run_doctor


def register(subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
    parser = subparsers.add_parser("doctor", help="Report workflow-specific environment readiness")
    parser.set_defaults(handler=run)


def run(args: argparse.Namespace, platform: Platform) -> None:
    run_doctor(platform, TerminalUi())
