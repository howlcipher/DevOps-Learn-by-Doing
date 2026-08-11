import sqlite3

import pytest

from devops_learn.domain.learner_profile_models import (
    CompetencyArea,
    LearnerProfile,
    ProficiencyLevel,
)
from devops_learn.learning.learner_profile_service import LearnerProfileService
from devops_learn.learning.persistence.repositories.learner_profile_repository import (
    LearnerProfileRepository,
)


def test_repository_round_trips_profile(conn: sqlite3.Connection) -> None:
    repo = LearnerProfileRepository(conn)
    profile = LearnerProfile(
        proficiencies={
            CompetencyArea.DOCKER: ProficiencyLevel.STRONG,
            CompetencyArea.TERRAFORM: ProficiencyLevel.BEGINNER,
        },
        learning_focus=(CompetencyArea.TERRAFORM, CompetencyArea.AZURE),
    )
    saved = repo.save(profile)
    loaded = repo.load()
    assert loaded is not None
    assert loaded.proficiencies == saved.proficiencies
    assert loaded.learning_focus == saved.learning_focus


def test_service_returns_empty_profile_when_none_exists(
    conn: sqlite3.Connection,
) -> None:
    service = LearnerProfileService(LearnerProfileRepository(conn))
    profile = service.load()
    assert profile.proficiencies == {}
    assert profile.learning_focus == ()


def test_service_parses_area_and_level_strings(conn: sqlite3.Connection) -> None:
    service = LearnerProfileService(LearnerProfileRepository(conn))
    assert service.parse_area("docker") is CompetencyArea.DOCKER
    assert service.parse_area("ci/cd") is CompetencyArea.CI_CD
    assert service.parse_level("beginner") is ProficiencyLevel.BEGINNER
    assert service.parse_level("strong") is ProficiencyLevel.STRONG


def test_service_rejects_unknown_area(conn: sqlite3.Connection) -> None:
    service = LearnerProfileService(LearnerProfileRepository(conn))
    with pytest.raises(ValueError):
        service.parse_area("unknown")


def test_profile_defaults_beginner_for_missing_areas() -> None:
    profile = LearnerProfile()
    assert profile.level(CompetencyArea.DOCKER) is ProficiencyLevel.BEGINNER
    assert not profile.is_strong(CompetencyArea.DOCKER)
    assert profile.is_beginner(CompetencyArea.DOCKER)
