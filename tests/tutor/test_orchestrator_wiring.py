import sqlite3
from datetime import datetime, timezone

from devops_learn.domain.enums import (
    AssistanceLevel,
    CloudProviderKind,
    ExplanationDepth,
    LanguageTrackKind,
)
from devops_learn.domain.learner_models import LearnerProfile
from devops_learn.tutor.bootstrap import build_platform

NOW = datetime(2026, 8, 9, 12, 0, 0, tzinfo=timezone.utc)


def _new_learner(conn: sqlite3.Connection) -> int:
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
    return profile.id


def test_build_platform_wires_a_working_orchestrator(conn: sqlite3.Connection) -> None:
    platform = build_platform(conn)
    assert platform.orchestrator is not None
    assert platform.curriculum_service.project.id == "api_platform"


def test_begin_project_lands_on_module_one_with_a_menu(conn: sqlite3.Connection) -> None:
    platform = build_platform(conn)
    learner_id = _new_learner(conn)

    turn = platform.orchestrator.begin_project(
        learner_id=learner_id,
        project_id=platform.curriculum_service.project.id,
        simulation_mode=True,
        level=AssistanceLevel.GUIDED,
        depth=ExplanationDepth.LEARNING,
    )

    assert "Understand the workload" in turn.heading
    assert turn.session.current_task_id == "task_understand_health_and_info"
    menu_labels = [o.label for o in turn.menu]
    assert "Inspect the Python application" in menu_labels


def test_orchestrator_wiring_supports_resume_after_begin(conn: sqlite3.Connection) -> None:
    platform = build_platform(conn)
    learner_id = _new_learner(conn)

    begin_turn = platform.orchestrator.begin_project(
        learner_id=learner_id,
        project_id=platform.curriculum_service.project.id,
        simulation_mode=True,
        level=AssistanceLevel.GUIDED,
        depth=ExplanationDepth.LEARNING,
    )

    resumed_session = platform.session_service.resume_latest(learner_id)
    assert resumed_session is not None

    resume_turn = platform.orchestrator.resume(
        resumed_session, level=AssistanceLevel.GUIDED, depth=ExplanationDepth.LEARNING
    )
    assert resume_turn.session.current_task_id == begin_turn.session.current_task_id
