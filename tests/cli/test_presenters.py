from datetime import datetime, timezone

import pytest

from devops_learn.cli.presenters import render_turn
from devops_learn.domain.content import (
    ChoiceOption,
    ComprehensionQuestion,
    ContentBlock,
    MenuOption,
    PredictionPrompt,
)
from devops_learn.domain.enums import ContentBlockKind, SessionStatus
from devops_learn.domain.learner_models import LearningSession
from devops_learn.tutor.orchestrator import TurnResult

NOW = datetime(2026, 8, 9, 12, 0, 0, tzinfo=timezone.utc)


def _session() -> LearningSession:
    return LearningSession(
        id=1,
        learner_id=1,
        project_id="api_platform",
        status=SessionStatus.ACTIVE,
        simulation_mode=True,
        started_at=NOW,
        last_active_at=NOW,
    )


def test_render_turn_prints_why_what_and_question_headers(
    capsys: pytest.CaptureFixture[str],
) -> None:
    question = ComprehensionQuestion(
        prompt="What is the primary DevOps value of a health endpoint?",
        options=(
            ChoiceOption("A", "It encrypts requests"),
            ChoiceOption("B", "It lets systems determine application health"),
        ),
        correct_key="B",
        explanation_correct="Correct.",
        explanation_incorrect="Not quite.",
    )
    turn = TurnResult(
        session=_session(),
        heading="Understand the workload",
        blocks=(
            ContentBlock(kind=ContentBlockKind.WHY, text="Why this matters."),
            ContentBlock(kind=ContentBlockKind.WHAT, text="What it is."),
            ContentBlock(kind=ContentBlockKind.CHECK_QUESTION, text="q", question=question),
        ),
        menu=(MenuOption("A", "Inspect the app"), MenuOption("B", "Run it")),
    )

    render_turn(turn)
    output = capsys.readouterr().out

    assert "WHY" in output
    assert "Why this matters." in output
    assert "WHAT" in output
    assert "QUESTION" in output
    assert "What is the primary DevOps value of a health endpoint?" in output
    assert "A. It encrypts requests" in output
    assert "OPTIONS" in output
    assert "A. Inspect the app" in output


def test_render_turn_prompts_for_a_prediction_before_the_status_message(
    capsys: pytest.CaptureFixture[str],
) -> None:
    turn = TurnResult(
        session=_session(),
        heading="Containerize",
        prediction=PredictionPrompt(
            prompt="What happens when you build without a .dockerignore?",
            outcome_summary="The build context includes .git and is slower.",
        ),
        status_message="Waiting on your prediction.",
    )

    render_turn(turn)
    output = capsys.readouterr().out

    assert "PREDICTION" in output
    assert "What happens when you build without a .dockerignore?" in output
    assert "(type your prediction and press enter)" in output
    assert output.index("PREDICTION") < output.index("Waiting on your prediction.")
    # The outcome is never leaked before the learner answers.
    assert "includes .git" not in output


def test_render_turn_does_not_print_menu_blocks_twice(
    capsys: pytest.CaptureFixture[str],
) -> None:
    turn = TurnResult(
        session=_session(),
        heading="Containerize",
        blocks=(
            ContentBlock(
                kind=ContentBlockKind.NEXT_STEP_MENU,
                text="never rendered inline",
                menu_options=(MenuOption("A", "Write the Dockerfile"),),
            ),
            ContentBlock(kind=ContentBlockKind.HOW, text="docker build -t app ."),
        ),
        menu=(MenuOption("A", "Write the Dockerfile"),),
    )

    render_turn(turn)
    output = capsys.readouterr().out

    assert "never rendered inline" not in output
    assert output.count("A. Write the Dockerfile") == 1
    assert "docker build -t app ." in output


def test_render_turn_marks_terminal_sessions(capsys: pytest.CaptureFixture[str]) -> None:
    turn = TurnResult(
        session=_session(),
        heading="Project complete",
        status_message="Done.",
        is_terminal=True,
    )
    render_turn(turn)
    output = capsys.readouterr().out
    assert "(session complete)" in output
