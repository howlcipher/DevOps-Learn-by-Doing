"""DecisionService: records human decisions on ClarifyingQuestions and
Recommendations.

Distinct from tools/approval.py's ApprovalGate, which gates individual
destructive/high-risk Tool operations. A Decision here is an architectural or
prioritization choice ("use workload identity", "production-like"), not a
go/no-go on one specific tool call.
"""

from __future__ import annotations

from datetime import datetime, timezone

from devops_learn.domain.question_models import Decision
from devops_learn.learning.persistence.repositories.decision_repository import (
    DecisionRepository,
)


class DecisionService:
    def __init__(self, decision_repository: DecisionRepository) -> None:
        self._decision_repository = decision_repository

    def record(
        self,
        session_id: int,
        *,
        subject_kind: str,
        subject_id: str,
        outcome: str,
        detail: str | None = None,
    ) -> Decision:
        decision = Decision(
            subject_kind=subject_kind,
            subject_id=subject_id,
            outcome=outcome,
            detail=detail,
            decided_at=datetime.now(timezone.utc),
        )
        return self._decision_repository.record(session_id, decision)

    def history(self, session_id: int) -> list[Decision]:
        return self._decision_repository.list_for_session(session_id)
