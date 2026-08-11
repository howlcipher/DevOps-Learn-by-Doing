"""Experience/evidence tracking: what the user was actually exposed to or did.

This is deliberately not a mastery model like the old competency system it
replaces. concept is a free-text grouping label (e.g. "Terraform", "Docker",
"Kubernetes") rather than a fixed catalog code, because the platform now
operates on arbitrary real projects rather than one authored curriculum.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from devops_learn.domain.enums import ExperienceState


@dataclass(frozen=True)
class ExperienceEntry:
    session_id: int
    concept: str
    item: str
    state: ExperienceState
    occurred_at: datetime
    id: int | None = None
