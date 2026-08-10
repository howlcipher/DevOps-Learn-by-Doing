import sqlite3
from collections.abc import Iterator
from datetime import datetime, timezone

import pytest

from devops_learn.domain.enums import (
    AssistanceLevel,
    CloudProviderKind,
    ExplanationDepth,
    LanguageTrackKind,
    SessionStatus,
)
from devops_learn.domain.learner_models import LearnerProfile, LearningSession
from devops_learn.learning.persistence.connection import connect_in_memory
from devops_learn.learning.persistence.migrations import ensure_schema
from devops_learn.learning.persistence.repositories.learner_profile_repository import (
    LearnerProfileRepository,
)
from devops_learn.learning.persistence.repositories.session_repository import SessionRepository

FIXED_NOW = datetime(2026, 8, 9, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture()
def conn() -> Iterator[sqlite3.Connection]:
    connection = connect_in_memory()
    ensure_schema(connection)
    yield connection
    connection.close()


@pytest.fixture()
def seeded_session(conn: sqlite3.Connection) -> tuple[int, int]:
    """A real learner_profiles + learning_sessions row pair, for FK-constrained tests."""
    profile = LearnerProfileRepository(conn).create(
        LearnerProfile(
            display_name="Learner",
            cloud_provider=CloudProviderKind.AZURE,
            language_track=LanguageTrackKind.PYTHON,
            assistance_level=AssistanceLevel.GUIDED,
            explanation_depth=ExplanationDepth.NORMAL,
            created_at=FIXED_NOW,
            updated_at=FIXED_NOW,
        )
    )
    assert profile.id is not None
    session = SessionRepository(conn).create(
        LearningSession(
            learner_id=profile.id,
            project_id="api_platform",
            status=SessionStatus.ACTIVE,
            simulation_mode=True,
            started_at=FIXED_NOW,
            last_active_at=FIXED_NOW,
        )
    )
    assert session.id is not None
    return profile.id, session.id
