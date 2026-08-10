"""Dispatch-level tests for the interactive REPL.

session_loop._dispatch is where raw learner input becomes an orchestrator call,
so every "the engine works but the CLI cannot reach it" bug lives here rather
than in the service tests.
"""

import dataclasses
import sqlite3
from datetime import datetime, timezone

import pytest

from devops_learn.cli.session_loop import _dispatch
from devops_learn.domain.enums import (
    AssistanceLevel,
    CloudProviderKind,
    ExplanationDepth,
    LanguageTrackKind,
)
from devops_learn.domain.learner_models import LearnerProfile
from devops_learn.tutor.bootstrap import Platform, build_platform
from devops_learn.tutor.orchestrator import TurnResult

NOW = datetime(2026, 8, 10, 12, 0, 0, tzinfo=timezone.utc)
LEVEL = AssistanceLevel.GUIDED
DEPTH = ExplanationDepth.LEARNING


@pytest.fixture()
def platform(conn: sqlite3.Connection) -> Platform:
    return build_platform(conn)


@pytest.fixture()
def first_turn(platform: Platform) -> TurnResult:
    profile = platform.profile_repository.create(
        LearnerProfile(
            display_name="Learner",
            cloud_provider=CloudProviderKind.AZURE,
            language_track=LanguageTrackKind.PYTHON,
            assistance_level=LEVEL,
            explanation_depth=DEPTH,
            created_at=NOW,
            updated_at=NOW,
        )
    )
    assert profile.id is not None
    return platform.orchestrator.begin_project(
        learner_id=profile.id,
        project_id=platform.curriculum_service.project.id,
        simulation_mode=True,
        level=LEVEL,
        depth=DEPTH,
    )


def send(platform: Platform, turn: TurnResult, text: str) -> TurnResult:
    return _dispatch(platform, turn, text, level=LEVEL, depth=DEPTH)


def test_letters_answer_the_question_while_it_is_displayed(
    platform: Platform, first_turn: TurnResult
) -> None:
    assert first_turn.question_keys == ("A", "B", "C", "D")
    turn = send(platform, first_turn, "B")
    assert turn.status_message is not None and "Correct" in turn.status_message


def test_the_same_letters_reach_the_menu_once_the_question_is_answered(
    platform: Platform, first_turn: TurnResult
) -> None:
    """Module 1 offers a question and a menu both keyed A-D; neither may shadow the other."""
    answered = send(platform, first_turn, "B")
    assert [o.label for o in answered.menu] == [
        "Inspect the Python application",
        "Run it",
        "Explain the code",
        "Show me the entire project roadmap",
    ]

    turn = send(platform, answered, "D")
    assert turn.heading == "PROJECT ROADMAP"
    assert turn.status_message is not None and "Containerize" in turn.status_message


def test_an_unrecognized_menu_label_does_not_silently_skip_the_task(
    platform: Platform, first_turn: TurnResult
) -> None:
    answered = send(platform, first_turn, "B")
    turn = send(platform, answered, "A")  # "Inspect the Python application"
    assert turn.session.current_task_id == first_turn.session.current_task_id
    assert turn.status_message is not None and "isn't wired up yet" in turn.status_message


def test_a_letter_still_answers_the_question_after_an_intervening_hint(
    platform: Platform, first_turn: TurnResult
) -> None:
    hinted = send(platform, first_turn, "hint")
    turn = send(platform, hinted, "B")
    assert turn.status_message is not None and "Correct" in turn.status_message


def test_hint_on_a_lesson_without_a_task_does_not_crash(
    platform: Platform, first_turn: TurnResult
) -> None:
    turn = first_turn
    while turn.session.current_module_id != "module_05_kubernetes_overview":
        turn = send(platform, turn, "continue")
    assert turn.session.current_task_id is None

    turn = send(platform, turn, "hint")
    assert turn.status_message is not None and "no task" in turn.status_message.lower()


def test_unknown_input_is_reported_rather_than_advancing(
    platform: Platform, first_turn: TurnResult
) -> None:
    turn = send(platform, first_turn, "?????")
    assert turn.session.current_task_id == first_turn.session.current_task_id
    assert turn.status_message is not None and "didn't understand" in turn.status_message


def test_a_pointer_at_content_that_no_longer_exists_is_re_anchored(
    platform: Platform, first_turn: TurnResult
) -> None:
    """Content ids are persisted, so renaming a task must not strand a saved session."""
    stale = dataclasses.replace(first_turn.session, current_task_id="task_renamed_in_a_later_v")

    turn = platform.orchestrator.resume(stale, level=LEVEL, depth=DEPTH)

    assert turn.session.current_task_id == "task_understand_health_and_info"
    assert turn.status_message is not None and "content changed" in turn.status_message
