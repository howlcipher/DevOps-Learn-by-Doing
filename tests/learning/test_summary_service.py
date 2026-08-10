import sqlite3
from datetime import datetime, timezone

from devops_learn.domain.competency_models import LearnerCompetency
from devops_learn.domain.enums import (
    AssistanceLevel,
    CloudProviderKind,
    CompetencyCode,
    CompetencyState,
    ExplanationDepth,
    LanguageTrackKind,
    LearningEventType,
    SessionStatus,
)
from devops_learn.domain.event_models import LearningEvent
from devops_learn.domain.learner_models import LearnerProfile, LearningSession
from devops_learn.learning.persistence.repositories.competency_repository import (
    CompetencyRepository,
)
from devops_learn.learning.persistence.repositories.event_repository import EventRepository
from devops_learn.learning.persistence.repositories.learner_profile_repository import (
    LearnerProfileRepository,
)
from devops_learn.learning.persistence.repositories.session_repository import SessionRepository
from devops_learn.learning.summary_service import SummaryService

NOW = datetime(2026, 8, 9, 12, 0, 0, tzinfo=timezone.utc)


def test_summary_reflects_real_persisted_state_not_placeholder_text(
    conn: sqlite3.Connection,
) -> None:
    profile = LearnerProfileRepository(conn).create(
        LearnerProfile(
            display_name="Learner",
            cloud_provider=CloudProviderKind.AZURE,
            language_track=LanguageTrackKind.PYTHON,
            assistance_level=AssistanceLevel.GUIDED,
            explanation_depth=ExplanationDepth.NORMAL,
            created_at=NOW,
            updated_at=NOW,
        )
    )
    assert profile.id is not None
    session = SessionRepository(conn).create(
        LearningSession(
            learner_id=profile.id,
            project_id="api_platform",
            status=SessionStatus.ACTIVE,
            simulation_mode=True,
            started_at=NOW,
            last_active_at=NOW,
        )
    )
    assert session.id is not None

    CompetencyRepository(conn).upsert_state(
        LearnerCompetency(
            learner_id=profile.id,
            code=CompetencyCode.DOCKER,
            state=CompetencyState.PRACTICED,
            updated_at=NOW,
        )
    )
    event_repo = EventRepository(conn)
    event_repo.append(
        LearningEvent(
            session_id=session.id,
            learner_id=profile.id,
            sequence_no=1,
            event_type=LearningEventType.DIAGNOSIS_ATTEMPTED,
            occurred_at=NOW,
            payload={"correct": True, "hints_used": 1},
        )
    )

    summary = SummaryService(CompetencyRepository(conn), event_repo).build_summary(profile.id)

    assert "docker: Practiced" in summary.competency_lines
    assert any("diagnosed one failure with 1 hint" in line for line in summary.narrative_lines)
    assert "docker" in summary.recommended_next_step


def test_summary_with_no_history_is_still_meaningful(conn: sqlite3.Connection) -> None:
    summary = SummaryService(
        CompetencyRepository(conn), EventRepository(conn)
    ).build_summary(learner_id=1)
    assert summary.competency_lines == ("No competencies tracked yet.",)
    assert summary.narrative_lines == ("No activity recorded yet.",)
    assert summary.recommended_next_step == "Continue to the next module."
