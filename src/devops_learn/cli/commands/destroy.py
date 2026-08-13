"""CLI entry point for explicitly approved Azure learning-environment cleanup."""

from __future__ import annotations

import argparse

from devops_learn.bootstrap import Platform
from devops_learn.cli.terminal_ui import TerminalUi
from devops_learn.domain.enums import ExplanationDepth
from devops_learn.workflows.deploy_flow import DeployOptions, run_cleanup_flow


def register(subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
    parser = subparsers.add_parser(
        "destroy", help="Destroy and independently verify an Azure lab cleanup"
    )
    parser.add_argument("path", nargs="?", default="projects/api_platform")
    parser.add_argument("--location", default="eastus")
    parser.add_argument("--environment", default="learning")
    parser.set_defaults(handler=run)


def run(args: argparse.Namespace, platform: Platform) -> None:
    success = run_cleanup_flow(
        platform,
        TerminalUi(),
        DeployOptions(
            project_root=args.path,
            location=args.location,
            environment=args.environment,
            depth=ExplanationDepth.LEARNING,
        ),
    )
    if not success:
        raise SystemExit(2)
