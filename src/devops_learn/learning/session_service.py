"""EngagementSession lifecycle: start, resume-latest, complete."""

from __future__ import annotations

from datetime import datetime, timezone

from devops_learn.audit.service import AuditService
from devops_learn.domain.enums import (
    AuditEventType,
    CloudProviderKind,
    CostPriority,
    EnvironmentKind,
    ExplanationDepth,
    OperatingMode,
)
from devops_learn.domain.session_models import EngagementSession
from devops_learn.learning.persistence.repositories.session_repository import SessionRepository


class SessionService:
    def __init__(self, session_repository: SessionRepository, audit: AuditService) -> None:
        self._session_repository = session_repository
        self._audit = audit

    def start(
        self,
        *,
        project_root: str,
        mode: OperatingMode,
        explanation_depth: ExplanationDepth,
        cloud: CloudProviderKind,
        environment: EnvironmentKind,
        cost_priority: CostPriority,
        simulation_mode: bool,
    ) -> EngagementSession:
        now = datetime.now(timezone.utc)
        session = self._session_repository.create(
            EngagementSession(
                project_root=project_root,
                mode=mode,
                explanation_depth=explanation_depth,
                cloud=cloud,
                environment=environment,
                cost_priority=cost_priority,
                simulation_mode=simulation_mode,
                started_at=now,
            )
        )
        assert session.id is not None
        self._audit.record(
            session_id=session.id,
            event_type=AuditEventType.SESSION_STARTED,
            occurred_at=now,
            summary=f"Session started for {project_root} in {mode.value} mode",
            payload={"mode": mode.value, "cloud": cloud.value},
        )
        return session

    def latest(self) -> EngagementSession | None:
        return self._session_repository.latest()

    def complete(self, session: EngagementSession) -> EngagementSession:
        now = datetime.now(timezone.utc)
        updated = self._session_repository.complete(session, completed_at=now)
        assert updated.id is not None
        self._audit.record(
            session_id=updated.id,
            event_type=AuditEventType.SESSION_COMPLETED,
            occurred_at=now,
            summary="Session completed",
        )
        return updated
