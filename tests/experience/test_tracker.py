import sqlite3

from devops_learn.domain.enums import ExperienceState
from devops_learn.experience.tracker import ExperienceTracker
from devops_learn.learning.persistence.repositories.experience_repository import (
    ExperienceRepository,
)


def test_summary_groups_entries_by_concept(conn: sqlite3.Connection, seeded_session: int) -> None:
    tracker = ExperienceTracker(ExperienceRepository(conn))
    tracker.record(seeded_session, "Docker", "Reviewed Dockerfile", ExperienceState.OBSERVED)
    tracker.record(seeded_session, "Docker", "Built image", ExperienceState.PARTICIPATED)
    tracker.record(
        seeded_session, "Terraform", "Reviewed generated Terraform", ExperienceState.OBSERVED
    )

    summary = tracker.summary(seeded_session)
    assert {e.item for e in summary["Docker"]} == {"Reviewed Dockerfile", "Built image"}
    assert len(summary["Terraform"]) == 1


def test_recording_the_same_item_twice_updates_rather_than_duplicates(
    conn: sqlite3.Connection, seeded_session: int
) -> None:
    tracker = ExperienceTracker(ExperienceRepository(conn))
    tracker.record(seeded_session, "Docker", "Built image", ExperienceState.OBSERVED)
    tracker.record(seeded_session, "Docker", "Built image", ExperienceState.PARTICIPATED)

    summary = tracker.summary(seeded_session)
    assert len(summary["Docker"]) == 1
    assert summary["Docker"][0].state == ExperienceState.PARTICIPATED
