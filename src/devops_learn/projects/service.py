"""Orchestrates the learner's project artifacts and the tool calls that touch them.

Distinct from the top-level projects/api_platform/, which is the demo
application's actual source, not platform orchestration code.
"""

from __future__ import annotations

from datetime import datetime

from devops_learn.domain.enums import LearningEventType
from devops_learn.domain.project_models import Artifact
from devops_learn.learning.journal import LearningJournal
from devops_learn.learning.persistence.repositories.artifact_repository import (
    ArtifactRepository,
)
from devops_learn.tools.base import ToolResult
from devops_learn.tools.service import ToolService


class ProjectService:
    def __init__(
        self,
        tool_service: ToolService,
        artifact_repository: ArtifactRepository,
        journal: LearningJournal,
    ) -> None:
        self._tool_service = tool_service
        self._artifact_repository = artifact_repository
        self._journal = journal

    def record_artifact(
        self,
        *,
        session_id: int,
        learner_id: int,
        artifact_type: str,
        path_or_ref: str,
        occurred_at: datetime,
        triggering_event_id: int | None = None,
    ) -> Artifact:
        artifact = self._artifact_repository.create(
            Artifact(
                session_id=session_id,
                learner_id=learner_id,
                artifact_type=artifact_type,
                path_or_ref=path_or_ref,
                created_at=occurred_at,
                event_id=triggering_event_id,
            )
        )
        self._journal.record(
            session_id=session_id,
            learner_id=learner_id,
            event_type=LearningEventType.PROJECT_ARTIFACT_CREATED,
            occurred_at=occurred_at,
            payload={"artifact_type": artifact_type, "path_or_ref": path_or_ref},
        )
        return artifact

    def run_python_tests(self) -> ToolResult:
        return self._tool_service.invoke("python", "run_tests")

    def build_container_image(self) -> ToolResult:
        return self._tool_service.invoke("docker", "build")

    def run_container(self) -> ToolResult:
        return self._tool_service.invoke("docker", "run")
