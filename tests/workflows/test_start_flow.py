import sqlite3
from datetime import datetime, timezone

from devops_learn.curriculum.service import CurriculumService
from devops_learn.domain.enums import (
    AssistanceLevel,
    CloudProviderKind,
    ExplanationDepth,
    LanguageTrackKind,
)
from devops_learn.domain.learner_models import LearnerProfile
from devops_learn.learning.journal import LearningJournal
from devops_learn.learning.persistence.repositories.event_repository import EventRepository
from devops_learn.learning.persistence.repositories.learner_profile_repository import (
    LearnerProfileRepository,
)
from devops_learn.learning.persistence.repositories.session_repository import SessionRepository
from devops_learn.learning.session_service import SessionService
from devops_learn.workflows.start_flow import start_project

NOW = datetime(2026, 8, 9, 12, 0, 0, tzinfo=timezone.utc)


def test_start_project_sets_pointer_to_module_one_and_journals_lesson_started(
    conn: sqlite3.Connection,
) -> None:
    profile = LearnerProfileRepository(conn).create(
        LearnerProfile(
            display_name="Learner",
            cloud_provider=CloudProviderKind.AZURE,
            language_track=LanguageTrackKind.PYTHON,
            assistance_level=AssistanceLevel.GUIDED,
            explanation_depth=ExplanationDepth.NORMAL,
            created_at=NOW,
            updated_at=NOW,
        )
    )
    assert profile.id is not None

    session_service = SessionService(
        SessionRepository(conn), LearningJournal(EventRepository(conn))
    )
    curriculum_service = CurriculumService()

    result = start_project(
        learner_id=profile.id,
        project_id=curriculum_service.project.id,
        simulation_mode=True,
        session_service=session_service,
        curriculum_service=curriculum_service,
        journal=LearningJournal(EventRepository(conn)),
    )

    assert result.module.id == "module_01_understand_workload"
    assert result.session.current_module_id == "module_01_understand_workload"
    assert result.session.current_task_id == "task_understand_health_and_info"

    assert result.session.id is not None
    events = EventRepository(conn).list_for_session(result.session.id)
    assert any(e.event_type.value == "lesson_started" for e in events)
