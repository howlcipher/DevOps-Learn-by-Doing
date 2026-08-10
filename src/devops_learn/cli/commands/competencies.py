"""`devops-learn competencies`: current competency states for the latest learner."""

from __future__ import annotations

import argparse

from devops_learn.tutor.bootstrap import Platform


def register(subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
    parser = subparsers.add_parser("competencies", help="Show your competency states")
    parser.set_defaults(handler=run)


def run(args: argparse.Namespace, platform: Platform) -> None:
    profile = platform.profile_repository.latest()
    if profile is None or profile.id is None:
        print("No learner profile yet. Run 'devops-learn start' first.")
        return

    states = platform.competency_repository.list_states(profile.id)
    if not states:
        print("No competencies tracked yet.")
        return
    for state in states:
        print(f"{state.code.value}: {state.state.name.title()}")
