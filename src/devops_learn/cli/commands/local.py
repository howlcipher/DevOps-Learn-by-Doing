"""`devops-learn local <path>`: run a real local vertical slice.

The local workflow inspects the project, runs real tests and lint, builds and
runs a real Docker container, verifies the health endpoint, and optionally
injects a failure to practice troubleshooting.
"""

from __future__ import annotations

import argparse

from devops_learn.bootstrap import Platform
from devops_learn.cli.terminal_ui import TerminalUi
from devops_learn.workflows.local_flow import LocalOptions, run_local_flow


def register(subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
    parser = subparsers.add_parser(
        "local",
        help="Run the local vertical slice: inspect, test, Docker build, run, verify",
    )
    parser.add_argument("path", help="Path to the project to run locally")
    parser.add_argument(
        "--image-tag", default="api-platform:dev", help="Docker image tag to build"
    )
    parser.add_argument(
        "--container-name", default="api-platform-local", help="Name for the running container"
    )
    parser.add_argument(
        "--port", type=int, default=8000, help="Host port to map to container port 8000"
    )
    parser.add_argument(
        "--inject-failure",
        action="store_true",
        help="After success, inject a container failure to practice troubleshooting",
    )
    parser.set_defaults(handler=run)


def run(args: argparse.Namespace, platform: Platform) -> None:
    options = LocalOptions(
        project_root=args.path,
        image_tag=args.image_tag,
        container_name=args.container_name,
        host_port=args.port,
        inject_failure=args.inject_failure,
    )
    run_local_flow(platform, TerminalUi(), options)
