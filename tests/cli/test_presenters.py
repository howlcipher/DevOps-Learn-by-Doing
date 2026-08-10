from datetime import datetime, timezone

import pytest

from devops_learn.cli.presenters import render_turn
from devops_learn.domain.content import (
    ChoiceOption,
    ComprehensionQuestion,
    ContentBlock,
    MenuOption,
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
