import sqlite3
from datetime import datetime, timezone

from devops_learn.domain.attempt_models import HintUsage, TaskAttempt
from devops_learn.domain.competency_models import CompetencyTransition, LearnerCompetency
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
from devops_learn.domain.project_models import Artifact
from devops_learn.learning.persistence.repositories.artifact_repository import (
    ArtifactRepository,
)
from devops_learn.learning.persistence.repositories.competency_repository import (
    CompetencyRepository,
)
from devops_learn.learning.persistence.repositories.event_repository import EventRepository
from devops_learn.learning.persistence.repositories.learner_profile_repository import (
    LearnerProfileRepository,
)
from devops_learn.learning.persistence.repositories.session_repository import SessionRepository
from devops_learn.learning.persistence.repositories.task_attempt_repository import (
    TaskAttemptRepository,
)

NOW = datetime(2026, 8, 9, 12, 0, 0, tzinfo=timezone.utc)


def _make_profile() -> LearnerProfile:
    return LearnerProfile(
        display_name="Learner One",
        cloud_provider=CloudProviderKind.AZURE,
        language_track=LanguageTrackKind.PYTHON,
        assistance_level=AssistanceLevel.GUIDED,
        explanation_depth=ExplanationDepth.LEARNING,
        created_at=NOW,
        updated_at=NOW,
    )


def test_learner_profile_round_trips(conn: sqlite3.Connection) -> None:
    repo = LearnerProfileRepository(conn)
    created = repo.create(_make_profile())
    assert created.id is not None
    fetched = repo.get(created.id)
    assert fetched == created


def test_session_created_and_resumable_by_pointer(conn: sqlite3.Connection) -> None:
    profile_repo = LearnerProfileRepository(conn)
    profile = profile_repo.create(_make_profile())
    assert profile.id is not None

    session_repo = SessionRepository(conn)
    session = session_repo.create(
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

    updated = session_repo.update_pointer(
        LearningSession(
            id=session.id,
            learner_id=profile.id,
            project_id="api_platform",
            status=SessionStatus.ACTIVE,
            simulation_mode=True,
            started_at=NOW,
            last_active_at=NOW,
            current_module_id="module_02_containerize",
            current_lesson_id="lesson_containerize",
            current_task_id="task_write_dockerfile",
        )
    )
    assert updated.current_task_id == "task_write_dockerfile"

    resumed = session_repo.latest_active_for_learner(profile.id)
    assert resumed is not None
    assert resumed.current_task_id == "task_write_dockerfile"


def test_events_get_monotonic_sequence_numbers(conn: sqlite3.Connection) -> None:
    profile = LearnerProfileRepository(conn).create(_make_profile())
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

    event_repo = EventRepository(conn)
    first = event_repo.append(
        LearningEvent(
            session_id=session.id,
            learner_id=profile.id,
            sequence_no=event_repo.next_sequence_no(session.id),
            event_type=LearningEventType.SESSION_STARTED,
            occurred_at=NOW,
        )
    )
    second = event_repo.append(
        LearningEvent(
            session_id=session.id,
            learner_id=profile.id,
            sequence_no=event_repo.next_sequence_no(session.id),
            event_type=LearningEventType.LESSON_STARTED,
            occurred_at=NOW,
            payload={"lesson_id": "lesson_understand_workload"},
        )
    )
    assert first.sequence_no == 1
    assert second.sequence_no == 2

    events = event_repo.list_for_session(session.id)
    assert [e.sequence_no for e in events] == [1, 2]
    assert events[1].payload == {"lesson_id": "lesson_understand_workload"}


def test_competency_state_upsert_and_transition_history(conn: sqlite3.Connection) -> None:
    profile = LearnerProfileRepository(conn).create(_make_profile())
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
            event_type=LearningEventType.TASK_COMPLETED,
            occurred_at=NOW,
        )
    )
    assert event.id is not None

    repo = CompetencyRepository(conn)
    repo.upsert_state(
        LearnerCompetency(
            learner_id=profile.id,
            code=CompetencyCode.DOCKER,
            state=CompetencyState.INTRODUCED,
            updated_at=NOW,
        )
    )
    repo.upsert_state(
        LearnerCompetency(
            learner_id=profile.id,
            code=CompetencyCode.DOCKER,
            state=CompetencyState.DEMONSTRATED,
            updated_at=NOW,
            evidence_event_id=event.id,
        )
    )
    state = repo.get_state(profile.id, CompetencyCode.DOCKER)
    assert state is not None
    assert state.state == CompetencyState.DEMONSTRATED

    repo.record_transition(
        CompetencyTransition(
            learner_id=profile.id,
            code=CompetencyCode.DOCKER,
            from_state=CompetencyState.INTRODUCED,
            to_state=CompetencyState.DEMONSTRATED,
            triggering_event_id=event.id,
            occurred_at=NOW,
        )
    )
    transitions = repo.list_transitions(profile.id)
    assert len(transitions) == 1
    assert transitions[0].to_state == CompetencyState.DEMONSTRATED


def test_hint_usage_increments_task_attempt_hint_count(conn: sqlite3.Connection) -> None:
    profile = LearnerProfileRepository(conn).create(_make_profile())
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

    attempt_repo = TaskAttemptRepository(conn)
    attempt = attempt_repo.start_attempt(
        TaskAttempt(
            session_id=session.id,
            task_id="task_write_dockerfile",
            learner_id=profile.id,
            attempt_no=1,
            started_at=NOW,
        )
    )
    assert attempt.id is not None

    attempt_repo.record_hint_usage(
        HintUsage(task_attempt_id=attempt.id, hint_level=1, requested_at=NOW)
    )
    attempt_repo.record_hint_usage(
        HintUsage(task_attempt_id=attempt.id, hint_level=2, requested_at=NOW)
    )
    assert attempt_repo.count_hints_used(attempt.id) == 2

    completed = attempt_repo.complete_attempt(
        attempt, completed_at=NOW, outcome=TaskOutcome.SUCCESS
    )
    assert completed.outcome == TaskOutcome.SUCCESS


def test_artifact_created_and_listed(conn: sqlite3.Connection) -> None:
    profile = LearnerProfileRepository(conn).create(_make_profile())
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

    artifact_repo = ArtifactRepository(conn)
    artifact_repo.create(
        Artifact(
            session_id=session.id,
            learner_id=profile.id,
            artifact_type="dockerfile",
            path_or_ref="projects/api_platform/Dockerfile",
            created_at=NOW,
        )
    )
    artifacts = artifact_repo.list_for_session(session.id)
    assert len(artifacts) == 1
    assert artifacts[0].artifact_type == "dockerfile"
