"""Orchestrator paths the happy-path wiring tests never reach.

Covers content-only lessons (a lesson with no tasks, so the session pointer has
no current_task_id), hint exhaustion, the troubleshooting hint source, and the
guard against asking for a check question on a task that has none.
"""

import dataclasses
import sqlite3
from datetime import datetime, timezone

import pytest

from devops_learn.curriculum.service import CurriculumService
from devops_learn.domain.enums import (
    AssistanceLevel,
    CloudProviderKind,
    ExplanationDepth,
    LanguageTrackKind,
)
from devops_learn.domain.learner_models import LearnerProfile, LearningSession
from devops_learn.tutor.bootstrap import Platform, build_platform
from devops_learn.tutor.orchestrator import TurnResult
from devops_learn.workflows.troubleshooting_flow import scenario_for_task

NOW = datetime(2026, 8, 9, 12, 0, 0, tzinfo=timezone.utc)
CONTENT_ONLY_MODULE_ID = "module_05_kubernetes_overview"
TROUBLESHOOTING_TASK_ID = "troubleshoot_container_wont_start"


@pytest.fixture()
def platform(conn: sqlite3.Connection) -> Platform:
    return build_platform(conn)


@pytest.fixture()
def learner_id(platform: Platform) -> int:
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


def _begin(platform: Platform, learner_id: int) -> TurnResult:
    return platform.orchestrator.begin_project(
        learner_id=learner_id,
        project_id=platform.curriculum_service.project.id,
        simulation_mode=True,
        level=AssistanceLevel.GUIDED,
        depth=ExplanationDepth.LEARNING,
    )


def _move_to(platform: Platform, session: LearningSession, task_id: str) -> LearningSession:
    module, lesson = platform.curriculum_service.parents_of_task(task_id)
    return platform.session_service.advance_pointer(
        session, module_id=module.id, lesson_id=lesson.id, task_id=task_id
    )


def test_begin_project_renders_a_content_only_lesson_without_a_task(
    platform: Platform, learner_id: int
) -> None:
    project = platform.curriculum_service.project
    content_only_module = platform.curriculum_service.module(CONTENT_ONLY_MODULE_ID)
    assert content_only_module.lessons[0].tasks == ()
    platform.orchestrator._curriculum = CurriculumService(
        dataclasses.replace(project, modules=(content_only_module,))
    )

    turn = _begin(platform, learner_id)

    assert turn.session.current_task_id is None
    assert turn.heading == f"MODULE: {content_only_module.title}"
    assert turn.blocks != ()


def test_resume_renders_a_content_only_lesson_from_the_stored_pointer(
    platform: Platform, learner_id: int
) -> None:
    session = _begin(platform, learner_id).session
    module = platform.curriculum_service.module(CONTENT_ONLY_MODULE_ID)
    lesson = module.lessons[0]
    session = platform.session_service.advance_pointer(
        session, module_id=module.id, lesson_id=lesson.id, task_id=None
    )

    turn = platform.orchestrator.resume(
        session, level=AssistanceLevel.GUIDED, depth=ExplanationDepth.LEARNING
    )

    assert turn.heading == f"MODULE: {module.title}"
    assert turn.blocks != ()
    assert turn.session.current_task_id is None


def test_hints_run_out_and_say_so_instead_of_repeating_the_last_one(
    platform: Platform, learner_id: int
) -> None:
    session = _begin(platform, learner_id).session
    assert session.current_task_id is not None
    hint_count = len(platform.curriculum_service.task(session.current_task_id).hints)

    messages = [
        platform.orchestrator.request_hint(session).status_message
        for _ in range(hint_count + 1)
    ]

    assert all(message is not None and message.startswith("HINT ") for message in messages[:-1])
    assert messages[-1] == (
        "No more hints available. Ask for the full explanation if you're stuck."
    )


def test_hints_for_a_troubleshooting_task_come_from_its_scenario(
    platform: Platform, learner_id: int
) -> None:
    session = _move_to(platform, _begin(platform, learner_id).session, TROUBLESHOOTING_TASK_ID)
    scenario = scenario_for_task(TROUBLESHOOTING_TASK_ID)
    assert scenario is not None

    turn = platform.orchestrator.request_hint(session)

    assert turn.status_message == f"HINT {scenario.hints[0].level}: {scenario.hints[0].text}"


def test_answering_a_check_question_on_a_task_without_one_is_a_programming_error(
    platform: Platform, learner_id: int
) -> None:
    session = _move_to(platform, _begin(platform, learner_id).session, "task_write_dockerfile")

    with pytest.raises(ValueError, match="has no check question"):
        platform.orchestrator.answer_question(session, chosen_key="A")
