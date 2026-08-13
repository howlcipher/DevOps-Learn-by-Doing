"""`devops-learn terraform [path]`: run the real Terraform vertical slice.

Runs real fmt/init/validate/plan against <path>/infra/terraform via
RealTerraformTool. This milestone ships real execution only against the
bundled projects/api_platform sample; generating configuration for arbitrary
projects is future work (see docs/roadmap.md).
"""

from __future__ import annotations

import argparse
from pathlib import Path

from devops_learn.bootstrap import Platform
from devops_learn.cli.terminal_ui import TerminalUi
from devops_learn.workflows.terraform_flow import TerraformOptions, run_terraform_flow


def register(subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
    parser = subparsers.add_parser(
        "terraform",
        help="Run the real Terraform vertical slice: fmt, init, validate, plan, risk analysis",
    )
    parser.add_argument(
        "path",
        nargs="?",
        default="projects/api_platform",
        help="Project containing infra/terraform/ (defaults to the bundled sample project)",
    )
    parser.set_defaults(handler=run)


def run(args: argparse.Namespace, platform: Platform) -> None:
    infra_root = f"{args.path}/infra/terraform"
    if not Path(infra_root).is_dir():
        print(f"No Terraform configuration found at {infra_root}.")
        print(
            "This milestone ships real Terraform execution only against the bundled "
            "projects/api_platform sample; generating configuration for arbitrary projects "
            "is future work (see docs/roadmap.md)."
        )
        return
    options = TerraformOptions(project_root=args.path, infra_root=infra_root)
    run_terraform_flow(platform, TerminalUi(), options)
