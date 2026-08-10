import sqlite3
from datetime import datetime, timezone

from devops_learn.competencies.service import CompetencyService
from devops_learn.domain.enums import (
    AssistanceLevel,
    CloudProviderKind,
    CompetencyCode,
    CompetencyState,
    ExplanationDepth,
    LanguageTrackKind,
    LearningEventType,
    SessionStatus,
    TaskOutcome,
)
from devops_learn.domain.event_models import LearningEvent
from devops_learn.domain.learner_models import LearnerProfile, LearningSession
from devops_learn.learning.journal import LearningJournal
from devops_learn.learning.persistence.repositories.competency_repository import (
    CompetencyRepository,
)
from devops_learn.learning.persistence.repositories.event_repository import EventRepository
from devops_learn.learning.persistence.repositories.learner_profile_repository import (
    LearnerProfileRepository,
)
from devops_learn.learning.persistence.repositories.session_repository import SessionRepository

NOW = datetime(2026, 8, 9, 12, 0, 0, tzinfo=timezone.utc)


def _service(conn: sqlite3.Connection) -> CompetencyService:
    return CompetencyService(CompetencyRepository(conn), LearningJournal(EventRepository(conn)))


def _seed_learner_and_session(conn: sqlite3.Connection) -> tuple[int, int, int]:
    """Competency rows FK to a real learner/session; unit tests must not skip that."""
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
    session = SessionRepository(conn).create(
        LearningSession(
            learner_id=profile.id,
            project_id="api_platform",
            status=SessionStatus.ACTIVE,
            simulation_mode=True,
            started_at=NOW,
            last_active_at=NOW,
        )
    )
    assert session.id is not None
    event = EventRepository(conn).append(
        LearningEvent(
            session_id=session.id,
            learner_id=profile.id,
            sequence_no=1,
            event_type=LearningEventType.TASK_ATTEMPTED,
            occurred_at=NOW,
        )
    )
    assert event.id is not None
    return profile.id, session.id, event.id


def test_record_content_viewed_only_reaches_introduced(conn: sqlite3.Connection) -> None:
    learner_id, session_id, event_id = _seed_learner_and_session(conn)
    service = _service(conn)
    results = service.record_content_viewed(
        session_id=session_id,
        learner_id=learner_id,
        codes=[CompetencyCode.DOCKER],
        triggering_event_id=event_id,
        occurred_at=NOW,
    )
    assert results[0].state == CompetencyState.INTRODUCED


def test_record_task_outcome_advances_and_journals_competency_advanced(
    conn: sqlite3.Connection,
) -> None:
    learner_id, session_id, event_id = _seed_learner_and_session(conn)
    service = _service(conn)
    service.record_task_outcome(
        session_id=session_id,
        learner_id=learner_id,
        codes=[CompetencyCode.DOCKER],
        outcome=TaskOutcome.SUCCESS,
        hints_used=0,
        total_hints=3,
        triggering_event_id=event_id,
        occurred_at=NOW,
    )
    states = service.list_states(learner_id)
    assert states[0].state == CompetencyState.DEMONSTRATED

    events = EventRepository(conn).list_for_session(session_id)
    advanced = [e for e in events if e.event_type == LearningEventType.COMPETENCY_ADVANCED]
    assert len(advanced) == 1
    assert advanced[0].payload["to_state"] == "DEMONSTRATED"


def test_a_later_worse_attempt_does_not_regress_demonstrated(conn: sqlite3.Connection) -> None:
    learner_id, session_id, event_id = _seed_learner_and_session(conn)
    service = _service(conn)
    service.record_task_outcome(
        session_id=session_id,
        learner_id=learner_id,
        codes=[CompetencyCode.DOCKER],
        outcome=TaskOutcome.SUCCESS,
        hints_used=0,
        total_hints=3,
        triggering_event_id=event_id,
        occurred_at=NOW,
    )
    service.record_task_outcome(
        session_id=session_id,
        learner_id=learner_id,
        codes=[CompetencyCode.DOCKER],
        outcome=TaskOutcome.FAILED,
        hints_used=0,
        total_hints=3,
        triggering_event_id=event_id,
        occurred_at=NOW,
    )
    states = service.list_states(learner_id)
    assert states[0].state == CompetencyState.DEMONSTRATED
