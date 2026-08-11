"""`devops-learn history`: prints the audit log for the most recent session."""

from __future__ import annotations

import argparse

from devops_learn.bootstrap import Platform


def register(subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
    parser = subparsers.add_parser("history", help="Show the audit log for the latest session.")
    parser.set_defaults(handler=run)


def run(args: argparse.Namespace, platform: Platform) -> None:
    session = platform.session_service.latest()
    if session is None or session.id is None:
        print("No sessions yet. Run 'devops-learn analyze <path>' first.")
        return
    for event in platform.audit_service.history(session.id):
        print(f"{event.occurred_at.isoformat()}  {event.event_type.value}: {event.summary}")
