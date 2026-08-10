"""`devops-learn resume`: continues the most recent active session."""

from __future__ import annotations

import argparse

from devops_learn.cli.session_loop import resume_interactive_session
from devops_learn.tutor.bootstrap import Platform


def register(subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
    parser = subparsers.add_parser("resume", help="Resume your most recent session")
    parser.set_defaults(handler=run)


def run(args: argparse.Namespace, platform: Platform) -> None:
    profile = platform.profile_repository.latest()
    if profile is None or profile.id is None:
        print("No previous session found. Run 'devops-learn start' first.")
        return

    session = platform.session_service.resume_latest(profile.id)
    if session is None:
        print("No active session to resume. Run 'devops-learn start' to begin a new one.")
        return

    resume_interactive_session(
        platform, session, level=profile.assistance_level, depth=profile.explanation_depth
    )
