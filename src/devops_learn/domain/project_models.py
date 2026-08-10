"""Learner-produced artifacts (e.g. a Dockerfile, a terraform plan output)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Artifact:
    session_id: int
    learner_id: int
    artifact_type: str
    path_or_ref: str
    created_at: datetime
    event_id: int | None = None
    id: int | None = None
