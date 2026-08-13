"""CLI entry point for the first real Azure deployment lifecycle."""

from __future__ import annotations

import argparse

from devops_learn.bootstrap import Platform
from devops_learn.cli.terminal_ui import TerminalUi
from devops_learn.domain.enums import ExplanationDepth
from devops_learn.workflows.deploy_flow import DeployOptions, run_deploy_flow


def register(subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
    parser = subparsers.add_parser(
        "deploy",
        help="Run the security-gated, approval-controlled real Azure deployment lifecycle",
    )
    parser.add_argument("path", nargs="?", default="projects/api_platform")
    parser.add_argument("--cloud", choices=("azure",), default="azure")
    parser.add_argument(
        "--depth", choices=("brief", "normal", "learning", "deep"), default="learning"
    )
    parser.add_argument("--location", default="eastus")
    parser.add_argument("--environment", default="learning")
    parser.add_argument("--base-ref", default="origin/main")
    parser.set_defaults(handler=run)


def run(args: argparse.Namespace, platform: Platform) -> None:
    run_deploy_flow(
        platform,
        TerminalUi(),
        DeployOptions(
            project_root=args.path,
            cloud=args.cloud,
            depth=ExplanationDepth[args.depth.upper()],
            location=args.location,
            environment=args.environment,
            base_ref=args.base_ref,
        ),
    )
