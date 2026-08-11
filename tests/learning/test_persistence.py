import sqlite3
from datetime import datetime, timezone

from devops_learn.domain.audit_models import AuditEvent
from devops_learn.domain.enums import (
    AuditEventType,
    CloudProviderKind,
    CostPriority,
    EnvironmentKind,
    ExperienceState,
    ExplanationDepth,
    OperatingMode,
)
from devops_learn.domain.experience_models import ExperienceEntry
from devops_learn.domain.project_models import Artifact
from devops_learn.domain.question_models import Decision
from devops_learn.domain.session_models import EngagementSession
from devops_learn.learning.persistence.repositories.artifact_repository import (
    ArtifactRepository,
)
from devops_learn.learning.persistence.repositories.audit_repository import AuditRepository
from devops_learn.learning.persistence.repositories.decision_repository import (
    DecisionRepository,
)
from devops_learn.learning.persistence.repositories.experience_repository import (
    ExperienceRepository,
)
from devops_learn.learning.persistence.repositories.session_repository import SessionRepository

NOW = datetime(2026, 8, 9, 12, 0, 0, tzinfo=timezone.utc)


def _make_session() -> EngagementSession:
    return EngagementSession(
        project_root="/tmp/example",
        mode=OperatingMode.COLLABORATE,
        explanation_depth=ExplanationDepth.LEARNING,
        cloud=CloudProviderKind.AZURE,
        environment=EnvironmentKind.DEV,
        cost_priority=CostPriority.BALANCED,
        simulation_mode=True,
        started_at=NOW,
    )


def test_session_round_trips_and_can_be_completed(conn: sqlite3.Connection) -> None:
    repo = SessionRepository(conn)
    created = repo.create(_make_session())
    assert created.id is not None
    fetched = repo.get(created.id)
    assert fetched == created

    completed = repo.complete(created, completed_at=NOW)
    assert completed.completed_at == NOW
    assert repo.latest() is not None
    assert repo.latest().id == created.id  # type: ignore[union-attr]


def test_audit_events_get_monotonic_sequence_numbers(conn: sqlite3.Connection) -> None:
    session = SessionRepository(conn).create(_make_session())
    assert session.id is not None

    audit_repo = AuditRepository(conn)
    first = audit_repo.append(
        AuditEvent(
            session_id=session.id,
            sequence_no=audit_repo.next_sequence_no(session.id),
            event_type=AuditEventType.SESSION_STARTED,
            occurred_at=NOW,
            summary="Session started",
        )
    )
    second = audit_repo.append(
        AuditEvent(
            session_id=session.id,
            sequence_no=audit_repo.next_sequence_no(session.id),
            event_type=AuditEventType.PROJECT_ANALYZED,
            occurred_at=NOW,
            summary="Analyzed",
            payload={"language": "python"},
        )
    )
    assert first.sequence_no == 1
    assert second.sequence_no == 2

    events = audit_repo.list_for_session(session.id)
    assert [e.sequence_no for e in events] == [1, 2]
    assert events[1].payload == {"language": "python"}


def test_decisions_are_recorded_and_listed(conn: sqlite3.Connection) -> None:
    session = SessionRepository(conn).create(_make_session())
    assert session.id is not None

    repo = DecisionRepository(conn)
    repo.record(
        session.id,
        Decision(
            subject_kind="question",
            subject_id="environment",
            outcome="Production-like",
            detail=None,
            decided_at=NOW,
        ),
    )
    decisions = repo.list_for_session(session.id)
    assert len(decisions) == 1
    assert decisions[0].outcome == "Production-like"


def test_experience_entries_upsert_by_concept_and_item(conn: sqlite3.Connection) -> None:
    session = SessionRepository(conn).create(_make_session())
    assert session.id is not None

    repo = ExperienceRepository(conn)
    repo.record(
        ExperienceEntry(
            session_id=session.id,
            concept="Terraform",
            item="Reviewed generated Terraform",
            state=ExperienceState.OBSERVED,
            occurred_at=NOW,
        )
    )
    repo.record(
        ExperienceEntry(
            session_id=session.id,
            concept="Terraform",
            item="Reviewed generated Terraform",
            state=ExperienceState.PARTICIPATED,
            occurred_at=NOW,
        )
    )
    entries = repo.list_for_session(session.id)
    assert len(entries) == 1
    assert entries[0].state == ExperienceState.PARTICIPATED


def test_artifact_created_and_listed(conn: sqlite3.Connection) -> None:
    session = SessionRepository(conn).create(_make_session())
    assert session.id is not None

    artifact_repo = ArtifactRepository(conn)
    artifact_repo.create(
        Artifact(
            session_id=session.id,
            artifact_type="dockerfile",
            path_or_ref="projects/api_platform/Dockerfile",
            created_at=NOW,
        )
    )
    artifacts = artifact_repo.list_for_session(session.id)
    assert len(artifacts) == 1
    assert artifacts[0].artifact_type == "dockerfile"
