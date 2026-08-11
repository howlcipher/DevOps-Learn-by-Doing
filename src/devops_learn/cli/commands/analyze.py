"""`devops-learn analyze <path>`: the primary end-to-end workflow entry point."""

from __future__ import annotations

import argparse

from devops_learn.bootstrap import Platform
from devops_learn.cli.terminal_ui import TerminalUi
from devops_learn.domain.enums import (
    CloudProviderKind,
    CostPriority,
    EnvironmentKind,
    ExplanationDepth,
    OperatingMode,
)
from devops_learn.workflows.analyze_flow import AnalyzeOptions, run_analysis


def register(subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
    parser = subparsers.add_parser(
        "analyze", help="Analyze a project and, unless --mode review, build out its DevOps."
    )
    parser.add_argument("path", help="Path to the project to analyze")
    parser.add_argument(
        "--mode",
        choices=[m.value for m in OperatingMode],
        default=OperatingMode.COLLABORATE.value,
    )
    parser.add_argument(
        "--depth",
        choices=[d.name.lower() for d in ExplanationDepth],
        default=ExplanationDepth.NORMAL.name.lower(),
    )
    parser.add_argument(
        "--cloud",
        choices=[c.value for c in CloudProviderKind],
        default=CloudProviderKind.AZURE.value,
    )
    parser.add_argument("--environment", choices=[e.value for e in EnvironmentKind], default=None)
    parser.add_argument("--cost-priority", choices=[c.value for c in CostPriority], default=None)
    parser.add_argument(
        "--learn-kubernetes",
        action="store_true",
        help="Treat Kubernetes as a stated learning objective for this run.",
    )
    parser.add_argument(
        "--no-simulation",
        action="store_true",
        help="Reserved for future real execution; V1 always simulates. See docs/safety.md.",
    )
    parser.set_defaults(handler=run)


def run(args: argparse.Namespace, platform: Platform) -> None:
    options = AnalyzeOptions(
        project_root=args.path,
        mode=OperatingMode(args.mode),
        explanation_depth=ExplanationDepth[args.depth.upper()],
        cloud=CloudProviderKind(args.cloud),
        environment=EnvironmentKind(args.environment) if args.environment else None,
        cost_priority=CostPriority(args.cost_priority) if args.cost_priority else None,
        public_access=None,
        wants_kubernetes_experience=args.learn_kubernetes,
        simulation_mode=True,
    )
    run_analysis(platform, TerminalUi(), options)
