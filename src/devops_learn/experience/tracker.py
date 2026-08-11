"""ExperienceTracker: an evidence log of what the user was actually exposed to
or did, grouped by concept. Never claims mastery; see docs/adr/0008."""

from __future__ import annotations

from datetime import datetime, timezone

from devops_learn.domain.enums import ExperienceState
from devops_learn.domain.experience_models import ExperienceEntry
from devops_learn.learning.persistence.repositories.experience_repository import (
    ExperienceRepository,
)


class ExperienceTracker:
    def __init__(self, experience_repository: ExperienceRepository) -> None:
        self._experience_repository = experience_repository

    def record(self, session_id: int, concept: str, item: str, state: ExperienceState) -> None:
        self._experience_repository.record(
            ExperienceEntry(
                session_id=session_id,
                concept=concept,
                item=item,
                state=state,
                occurred_at=datetime.now(timezone.utc),
            )
        )

    def summary(self, session_id: int) -> dict[str, list[ExperienceEntry]]:
        grouped: dict[str, list[ExperienceEntry]] = {}
        for entry in self._experience_repository.list_for_session(session_id):
            grouped.setdefault(entry.concept, []).append(entry)
        return grouped
