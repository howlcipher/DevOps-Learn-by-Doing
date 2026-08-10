"""`devops-learn start`: onboarding prompts, then the interactive session loop."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from typing import Mapping, TypeVar

from devops_learn.cli.session_loop import run_interactive_session
from devops_learn.domain.enums import (
    AssistanceLevel,
    CloudProviderKind,
    ExplanationDepth,
    LanguageTrackKind,
)
from devops_learn.domain.learner_models import LearnerProfile
from devops_learn.tutor.bootstrap import Platform

T = TypeVar("T")

_ASSISTANCE_OPTIONS = {
    "1": AssistanceLevel.GUIDED,
    "2": AssistanceLevel.ASSISTED,
    "3": AssistanceLevel.CHALLENGE,
    "4": AssistanceLevel.INDEPENDENT,
}
_DEPTH_OPTIONS = {
    "1": ExplanationDepth.BRIEF,
    "2": ExplanationDepth.NORMAL,
    "3": ExplanationDepth.LEARNING,
    "4": ExplanationDepth.DEEP,
}
_QUIT_COMMANDS = {"quit", "exit"}


class _OnboardingAborted(Exception):
    """The learner ended onboarding with quit or end-of-input, before any profile exists."""


def _choose(options: Mapping[str, T], retry_message: str) -> T:
    """Prompt until a valid key is given. Quit or EOF aborts instead of looping forever."""
    while True:
        try:
            choice = input("> ").strip()
        except EOFError as exc:
            raise _OnboardingAborted from exc
        if choice.lower() in _QUIT_COMMANDS:
            raise _OnboardingAborted
        if choice in options:
            return options[choice]
        print(retry_message)


def register(subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
    parser = subparsers.add_parser("start", help="Start a new learning session")
    parser.add_argument(
        "--simulation",
        action="store_true",
        default=True,
        help="Run in simulation mode (default, and the only supported mode in V1)",
    )
    parser.set_defaults(handler=run)


def run(args: argparse.Namespace, platform: Platform) -> None:
    print("DEVOPS LEARN")
    print()
    print("Learn modern DevOps by building and operating real systems.")
    print()

    try:
        cloud = _choose_cloud()
        language = _choose_language()
        assistance = _choose_assistance()
        depth = _choose_depth()
    except _OnboardingAborted:
        print()
        print("Setup cancelled. Nothing was saved.")
        return

    now = datetime.now(timezone.utc)
    profile = platform.profile_repository.create(
        LearnerProfile(
            display_name="Learner",
            cloud_provider=cloud,
            language_track=language,
            assistance_level=assistance,
            explanation_depth=depth,
            created_at=now,
            updated_at=now,
        )
    )
    assert profile.id is not None

    print()
    print("PROJECT")
    print(platform.curriculum_service.project.title)

    run_interactive_session(
        platform, profile.id, level=assistance, depth=depth, simulation_mode=True
    )


def _choose_cloud() -> CloudProviderKind:
    print("Choose cloud:")
    print()
    print("1. Azure")
    print("2. AWS [coming soon]")
    print("3. GCP [coming soon]")
    print()
    return _choose(
        {"1": CloudProviderKind.AZURE},
        "AWS and GCP are not implemented yet. Please choose 1 (Azure).",
    )


def _choose_language() -> LanguageTrackKind:
    print()
    print("Choose application language:")
    print()
    print("1. Python")
    print("2. Go [coming soon]")
    print()
    return _choose(
        {"1": LanguageTrackKind.PYTHON},
        "Go is not implemented yet. Please choose 1 (Python).",
    )


def _choose_assistance() -> AssistanceLevel:
    print()
    print("Choose assistance:")
    print()
    for key, level in _ASSISTANCE_OPTIONS.items():
        print(f"{key}. {level.name.title()}")
    print()
    return _choose(_ASSISTANCE_OPTIONS, "Please choose 1-4.")


def _choose_depth() -> ExplanationDepth:
    print()
    print("Explanation depth:")
    print()
    for key, depth in _DEPTH_OPTIONS.items():
        print(f"{key}. {depth.name.title()}")
    print()
    return _choose(_DEPTH_OPTIONS, "Please choose 1-4.")
