import sqlite3

import pytest

from devops_learn.domain.enums import (
    AssistanceLevel,
    CloudProviderKind,
    ExplanationDepth,
    LanguageTrackKind,
)
from devops_learn.domain.learner_models import LearnerProfile
from devops_learn.tutor.bootstrap import Platform, build_platform

from tests.conftest import FIXED_NOW


@pytest.fixture()
def platform(conn: sqlite3.Connection) -> Platform:
    return build_platform(conn)


@pytest.fixture()
def learner_id(platform: Platform) -> int:
    """A persisted learner profile, so `latest()`-based commands find something."""
    profile = platform.profile_repository.create(
        LearnerProfile(
            display_name="Learner",
            cloud_provider=CloudProviderKind.AZURE,
            language_track=LanguageTrackKind.PYTHON,
            assistance_level=AssistanceLevel.CHALLENGE,
            explanation_depth=ExplanationDepth.DEEP,
            created_at=FIXED_NOW,
            updated_at=FIXED_NOW,
        )
    )
    assert profile.id is not None
    return profile.id
