import sqlite3
from datetime import datetime, timezone

from devops_learn.learning.journal import LearningJournal
from devops_learn.learning.persistence.repositories.artifact_repository import (
    ArtifactRepository,
)
from devops_learn.learning.persistence.repositories.event_repository import EventRepository
from devops_learn.projects.service import ProjectService
from devops_learn.tools.approval import AutoApproveApprovalGate
from devops_learn.tools.docker_tool import SimulatedDockerTool
from devops_learn.tools.python_tool import SimulatedPythonTool
from devops_learn.tools.service import ToolService

NOW = datetime(2026, 8, 9, 12, 0, 0, tzinfo=timezone.utc)


def _service(conn: sqlite3.Connection) -> ProjectService:
    tool_service = ToolService(
        {"python": SimulatedPythonTool(), "docker": SimulatedDockerTool()},
        AutoApproveApprovalGate(),
    )
    return ProjectService(
        tool_service, ArtifactRepository(conn), LearningJournal(EventRepository(conn))
    )


def test_record_artifact_persists_and_journals(
    conn: sqlite3.Connection, seeded_session: tuple[int, int]
) -> None:
    learner_id, session_id = seeded_session
    service = _service(conn)

    artifact = service.record_artifact(
        session_id=session_id,
        learner_id=learner_id,
        artifact_type="dockerfile",
        path_or_ref="projects/api_platform/Dockerfile",
        occurred_at=NOW,
    )
    assert artifact.id is not None

    events = EventRepository(conn).list_for_session(session_id)
    assert any(e.event_type.value == "project_artifact_created" for e in events)


def test_run_python_tests_delegates_to_tool_service(conn: sqlite3.Connection) -> None:
    result = _service(conn).run_python_tests()
    assert result.success is True


def test_build_and_run_container(conn: sqlite3.Connection) -> None:
    service = _service(conn)
    build = service.build_container_image()
    run = service.run_container()
    assert build.success is True
    assert run.success is True
