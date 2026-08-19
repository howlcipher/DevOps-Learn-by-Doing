"""`devops-learn troubleshoot`: diagnostic reasoning and deterministic recovery verification."""

from __future__ import annotations

import argparse
from typing import Any

from devops_learn.bootstrap import Platform
from devops_learn.cli.terminal_ui import TerminalUi
from devops_learn.workflows.troubleshooting_flow import (
    TroubleshootingOptions,
    list_troubleshooting_scenarios,
    run_troubleshooting_flow,
)


def register(subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
    parser = subparsers.add_parser(
        "troubleshoot",
        help="Troubleshooting scenarios with progressive assistance and recovery verification",
    )
    commands = parser.add_subparsers(dest="troubleshoot_command", required=True)

    # list
    list_cmd = commands.add_parser("list", help="List all available troubleshooting scenarios")
    list_cmd.set_defaults(handler=run_list)

    # run
    run_cmd = commands.add_parser("run", help="Start and solve a troubleshooting scenario")
    run_cmd.add_argument(
        "scenario",
        help="Scenario ID (e.g. port_conflict, missing_config, health_check_failure)",
    )
    run_cmd.add_argument(
        "--hint-level",
        type=int,
        choices=[0, 1, 2, 3, 4],
        default=None,
        help="Progressive hint level (0=evidence, 1=inspection, 2=subsystem, 3=cause, 4=fix)",
    )
    run_cmd.add_argument(
        "--remediation",
        type=str,
        default=None,
        help="Proposed remediation action or key=value parameter",
    )
    run_cmd.add_argument(
        "--real",
        action="store_true",
        help="Attempt real Docker/local tool execution if available",
    )
    run_cmd.add_argument(
        "--simulate",
        action="store_true",
        help="Force simulated execution mode for offline/test environments",
    )
    run_cmd.add_argument(
        "--path",
        default=".",
        help="Target project root directory",
    )
    run_cmd.set_defaults(handler=run_scenario)

    # doctor
    doc_cmd = commands.add_parser("doctor", help="Check environment readiness for troubleshooting")
    doc_cmd.set_defaults(handler=run_doctor)


def run_list(args: argparse.Namespace, platform: Platform) -> None:
    list_troubleshooting_scenarios(platform, TerminalUi())


def run_scenario(args: argparse.Namespace, platform: Platform) -> None:
    remediation_params: dict[str, Any] = {}
    if args.remediation and "=" in args.remediation:
        for item in args.remediation.split():
            if "=" in item:
                k, v = item.split("=", 1)
                remediation_params[k.strip()] = v.strip()

    simulate: bool | None = None
    if args.simulate:
        simulate = True
    elif args.real:
        simulate = False

    options = TroubleshootingOptions(
        scenario_id=args.scenario,
        hint_level=args.hint_level,
        remediation_action=args.remediation,
        remediation_params=remediation_params,
        project_root=args.path,
        simulate=simulate,
        interactive=args.remediation is None and args.hint_level is None,
    )
    evidence = run_troubleshooting_flow(platform, TerminalUi(), options)
    if not evidence.resolved and args.remediation is not None:
        raise SystemExit(1)


def run_doctor(args: argparse.Namespace, platform: Platform) -> None:
    from devops_learn.workflows.doctor_flow import run_doctor as execute_doctor
    execute_doctor(platform, TerminalUi())
