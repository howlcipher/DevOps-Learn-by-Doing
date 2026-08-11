import sqlite3
from collections.abc import Iterator
from datetime import datetime, timezone

import pytest

from devops_learn.domain.enums import (
    CloudProviderKind,
    CostPriority,
    EnvironmentKind,
    ExplanationDepth,
    OperatingMode,
)
from devops_learn.domain.session_models import EngagementSession
from devops_learn.learning.persistence.connection import connect_in_memory
from devops_learn.learning.persistence.migrations import ensure_schema
from devops_learn.learning.persistence.repositories.session_repository import SessionRepository

FIXED_NOW = datetime(2026, 8, 9, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture()
def conn() -> Iterator[sqlite3.Connection]:
    connection = connect_in_memory()
    ensure_schema(connection)
    yield connection
    connection.close()


@pytest.fixture()
def seeded_session(conn: sqlite3.Connection) -> int:
    """A real engagement_sessions row, for FK-constrained tests."""
    session = SessionRepository(conn).create(
        EngagementSession(
            project_root="/tmp/example",
            mode=OperatingMode.COLLABORATE,
            explanation_depth=ExplanationDepth.NORMAL,
            cloud=CloudProviderKind.AZURE,
            environment=EnvironmentKind.DEV,
            cost_priority=CostPriority.BALANCED,
            simulation_mode=True,
            started_at=FIXED_NOW,
        )
    )
    assert session.id is not None
    return session.id
