"""`devops-learn progress`: a summary built deterministically from persisted data."""

from __future__ import annotations

import argparse

from devops_learn.tutor.bootstrap import Platform


def register(subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
    parser = subparsers.add_parser("progress", help="Show your learning progress summary")
    parser.set_defaults(handler=run)


def run(args: argparse.Namespace, platform: Platform) -> None:
    profile = platform.profile_repository.latest()
    if profile is None or profile.id is None:
        print("No learner profile yet. Run 'devops-learn start' first.")
        return

    summary = platform.summary_service.build_summary(profile.id)
    print("TODAY'S PROGRESS")
    print()
    for line in summary.competency_lines:
        print(line)
    print()
    for line in summary.narrative_lines:
        print(line)
    print()
    print("Recommended next step:")
    print(summary.recommended_next_step)
