"""`devops-learn review <path>`: assessment and roadmap only, no implementation."""

from __future__ import annotations

import argparse

from devops_learn.bootstrap import Platform
from devops_learn.cli.terminal_ui import TerminalUi
from devops_learn.domain.enums import CloudProviderKind, ExplanationDepth, OperatingMode
from devops_learn.workflows.analyze_flow import AnalyzeOptions, run_analysis


def register(subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
    parser = subparsers.add_parser(
        "review", help="Evaluate an existing project's DevOps maturity; builds nothing."
    )
    parser.add_argument("path", help="Path to the project to review")
    parser.add_argument(
        "--learn-kubernetes",
        action="store_true",
        help="Treat Kubernetes as a stated learning objective when framing the roadmap.",
    )
    parser.set_defaults(handler=run)


def run(args: argparse.Namespace, platform: Platform) -> None:
    options = AnalyzeOptions(
        project_root=args.path,
        mode=OperatingMode.REVIEW,
        explanation_depth=ExplanationDepth.NORMAL,
        cloud=CloudProviderKind.AZURE,
        environment=None,
        cost_priority=None,
        public_access=None,
        wants_kubernetes_experience=args.learn_kubernetes,
        simulation_mode=True,
    )
    run_analysis(platform, TerminalUi(), options)
