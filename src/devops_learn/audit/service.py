"""AuditService: the sole writer of the append-only audit_events journal.

Every meaningful operation across the workflow should produce exactly one
AuditEvent through this service, so `history` can reconstruct what happened,
when, and why without inspecting any other table.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping

from devops_learn.domain.audit_models import AuditEvent
from devops_learn.domain.enums import AuditEventType
from devops_learn.learning.persistence.repositories.audit_repository import AuditRepository
from devops_learn.security.redaction import redact_data


class AuditService:
    def __init__(self, audit_repository: AuditRepository) -> None:
        self._audit_repository = audit_repository

    def record(
        self,
        *,
        session_id: int,
        event_type: AuditEventType,
        occurred_at: datetime,
        summary: str,
        payload: Mapping[str, Any] | None = None,
    ) -> AuditEvent:
        sequence_no = self._audit_repository.next_sequence_no(session_id)
        event = AuditEvent(
            session_id=session_id,
            sequence_no=sequence_no,
            event_type=event_type,
            occurred_at=occurred_at,
            summary=summary,
            payload=redact_data(payload or {}),
        )
        return self._audit_repository.append(event)

    def history(self, session_id: int) -> list[AuditEvent]:
        return self._audit_repository.list_for_session(session_id)
