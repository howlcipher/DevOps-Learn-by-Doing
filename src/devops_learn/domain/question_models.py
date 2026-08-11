"""Clarifying questions the platform asks, and the human's recorded answers.

QuestionService (questions/service.py) decides which of these are actually
material for a given ProjectAssessment; see docs/adr/0006.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class ClarifyingQuestion:
    id: str
    category: str
    prompt: str
    options: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class Decision:
    """One recorded human answer to a ClarifyingQuestion, or accept/modify/reject
    of a Recommendation. subject_id refers to either a question id or a
    recommendation id; which one is disambiguated by subject_kind."""

    subject_kind: str  # "question" | "recommendation"
    subject_id: str
    outcome: str
    detail: str | None
    decided_at: datetime
    id: int | None = None
