"""Validates begin_project's output matches the spec's required transcript shape:
module heading, WHY framing, a comprehension question, and a lettered next-step menu.
"""

import sqlite3
from datetime import datetime, timezone

from devops_learn.domain.content import ContentBlockKind
from devops_learn.domain.enums import (
    AssistanceLevel,
    CloudProviderKind,
    ExplanationDepth,
    LanguageTrackKind,
)
from devops_learn.domain.learner_models import LearnerProfile
from devops_learn.tutor.bootstrap import build_platform

NOW = datetime(2026, 8, 9, 12, 0, 0, tzinfo=timezone.utc)


def test_begin_project_matches_the_required_transcript_shape(conn: sqlite3.Connection) -> None:
    platform = build_platform(conn)
    profile = platform.profile_repository.create(
        LearnerProfile(
            display_name="Learner",
            cloud_provider=CloudProviderKind.AZURE,
            language_track=LanguageTrackKind.PYTHON,
            assistance_level=AssistanceLevel.GUIDED,
            explanation_depth=ExplanationDepth.LEARNING,
            created_at=NOW,
            updated_at=NOW,
        )
    )
    assert profile.id is not None

    turn = platform.orchestrator.begin_project(
        learner_id=profile.id,
        project_id=platform.curriculum_service.project.id,
        simulation_mode=True,
        level=AssistanceLevel.GUIDED,
        depth=ExplanationDepth.LEARNING,
    )

    assert "Understand the workload" in turn.heading

    kinds = [b.kind for b in turn.blocks]
    assert ContentBlockKind.WHY in kinds
    assert ContentBlockKind.WHAT in kinds
    assert ContentBlockKind.CHECK_QUESTION in kinds

    question_block = next(b for b in turn.blocks if b.kind == ContentBlockKind.CHECK_QUESTION)
    assert question_block.question is not None
    assert question_block.question.prompt == (
        "What is the primary DevOps value of a health endpoint?"
    )
    assert {o.key for o in question_block.question.options} == {"A", "B", "C", "D"}

    menu_labels = [o.label for o in turn.menu]
    assert menu_labels == [
        "Inspect the Python application",
        "Run it",
        "Explain the code",
        "Show me the entire project roadmap",
    ]


def test_answering_correctly_then_advancing_reaches_the_docker_module_with_hints_and_prediction(
    conn: sqlite3.Connection,
) -> None:
    platform = build_platform(conn)
    profile = platform.profile_repository.create(
        LearnerProfile(
            display_name="Learner",
            cloud_provider=CloudProviderKind.AZURE,
            language_track=LanguageTrackKind.PYTHON,
            assistance_level=AssistanceLevel.GUIDED,
            explanation_depth=ExplanationDepth.LEARNING,
            created_at=NOW,
            updated_at=NOW,
        )
    )
    assert profile.id is not None
    orchestrator = platform.orchestrator

    turn = orchestrator.begin_project(
        learner_id=profile.id,
        project_id=platform.curriculum_service.project.id,
        simulation_mode=True,
        level=AssistanceLevel.GUIDED,
        depth=ExplanationDepth.LEARNING,
    )
    turn = orchestrator.answer_question(turn.session, chosen_key="B")
    assert turn.status_message is not None and "Correct" in turn.status_message

    turn = orchestrator.advance(
        turn.session, level=AssistanceLevel.GUIDED, depth=ExplanationDepth.LEARNING
    )
    assert "Containerize" in turn.heading
    assert turn.prediction is not None

    hint_turn = orchestrator.request_hint(turn.session)
    assert hint_turn.status_message is not None and "HINT 1" in hint_turn.status_message
