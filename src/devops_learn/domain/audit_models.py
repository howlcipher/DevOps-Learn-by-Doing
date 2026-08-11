"""Append-only audit journal entries. See docs/safety.md and audit/service.py."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Mapping

from devops_learn.domain.enums import AuditEventType


@dataclass(frozen=True)
class AuditEvent:
    session_id: int
    sequence_no: int
    event_type: AuditEventType
    occurred_at: datetime
    summary: str
    payload: Mapping[str, Any] = field(default_factory=dict)
    id: int | None = None
