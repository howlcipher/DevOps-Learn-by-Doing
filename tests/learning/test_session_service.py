import sqlite3

from devops_learn.domain.enums import (
    AssistanceLevel,
    CloudProviderKind,
    ExplanationDepth,
    LanguageTrackKind,
    SessionStatus,
)
from devops_learn.domain.learner_models import LearnerProfile
from devops_learn.learning.journal import LearningJournal
from devops_learn.learning.persistence.repositories.event_repository import EventRepository
from devops_learn.learning.persistence.repositories.learner_profile_repository import (
    LearnerProfileRepository,
)
from devops_learn.learning.persistence.repositories.session_repository import SessionRepository
from devops_learn.learning.session_service import SessionService
from datetime import datetime, timezone

NOW = datetime(2026, 8, 9, 12, 0, 0, tzinfo=timezone.utc)


def _service(conn: sqlite3.Connection) -> SessionService:
    return SessionService(SessionRepository(conn), LearningJournal(EventRepository(conn)))


def _profile_id(conn: sqlite3.Connection) -> int:
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
    return profile.id


def test_start_new_session_is_active_and_journaled(conn: sqlite3.Connection) -> None:
    service = _service(conn)
    learner_id = _profile_id(conn)
    session = service.start_new_session(learner_id, "api_platform", simulation_mode=True)
    assert session.status == SessionStatus.ACTIVE
    assert session.id is not None

    events = EventRepository(conn).list_for_session(session.id)
    assert len(events) == 1


def test_advance_pointer_then_resume_returns_same_position(conn: sqlite3.Connection) -> None:
    service = _service(conn)
    learner_id = _profile_id(conn)
    session = service.start_new_session(learner_id, "api_platform", simulation_mode=True)

    service.advance_pointer(
        session,
        module_id="module_02_containerize",
        lesson_id="lesson_containerize",
        task_id="task_write_dockerfile",
    )

    resumed = service.resume_latest(learner_id)
    assert resumed is not None
    assert resumed.current_task_id == "task_write_dockerfile"


def test_resume_with_no_active_session_returns_none(conn: sqlite3.Connection) -> None:
    service = _service(conn)
    assert service.resume_latest(learner_id=999) is None


def test_complete_session_is_no_longer_resumable(conn: sqlite3.Connection) -> None:
    service = _service(conn)
    learner_id = _profile_id(conn)
    session = service.start_new_session(learner_id, "api_platform", simulation_mode=True)
    service.complete_session(session)
    assert service.resume_latest(learner_id) is None
