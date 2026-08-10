"""Begins a new session at the first module/lesson/task of a project.

A workflow function, not a service: it composes SessionService,
CurriculumService, and LearningJournal for one specific sequence, kept out of
TutorOrchestrator so the orchestrator stays a thin dispatcher.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from devops_learn.curriculum.service import CurriculumService
from devops_learn.domain.curriculum_models import Lesson, Module
from devops_learn.domain.enums import LearningEventType
from devops_learn.domain.learner_models import LearningSession
from devops_learn.learning.journal import LearningJournal
from devops_learn.learning.session_service import SessionService


@dataclass(frozen=True)
class StartResult:
    session: LearningSession
    module: Module
    lesson: Lesson


def start_project(
    *,
    learner_id: int,
    project_id: str,
    simulation_mode: bool,
    session_service: SessionService,
    curriculum_service: CurriculumService,
    journal: LearningJournal,
) -> StartResult:
    session = session_service.start_new_session(
        learner_id, project_id, simulation_mode=simulation_mode
    )
    assert session.id is not None
    session_id = session.id

    module = curriculum_service.first_module()
    lesson = module.lessons[0]
    first_task_id = lesson.tasks[0].id if lesson.tasks else None

    session = session_service.advance_pointer(
        session, module_id=module.id, lesson_id=lesson.id, task_id=first_task_id
    )
    journal.record(
        session_id=session_id,
        learner_id=learner_id,
        event_type=LearningEventType.LESSON_STARTED,
        occurred_at=datetime.now(timezone.utc),
        module_id=module.id,
        lesson_id=lesson.id,
    )
    return StartResult(session=session, module=module, lesson=lesson)
