import sqlite3

from devops_learn.domain.enums import ExperienceState
from devops_learn.experience.tracker import ExperienceTracker
from devops_learn.learning.persistence.repositories.experience_repository import (
    ExperienceRepository,
)


def test_summary_groups_entries_by_concept(conn: sqlite3.Connection, seeded_session: int) -> None:
    tracker = ExperienceTracker(ExperienceRepository(conn))
    tracker.record(seeded_session, "Docker", "Reviewed Dockerfile", ExperienceState.INTRODUCED)
    tracker.record(seeded_session, "Docker", "Built image", ExperienceState.PRACTICED)
    tracker.record(
        seeded_session, "Terraform", "Reviewed generated Terraform", ExperienceState.INTRODUCED
    )

    summary = tracker.summary(seeded_session)
    assert {e.item for e in summary["Docker"]} == {"Reviewed Dockerfile", "Built image"}
    assert len(summary["Terraform"]) == 1


def test_recording_the_same_item_twice_updates_rather_than_duplicates(
    conn: sqlite3.Connection, seeded_session: int
) -> None:
    tracker = ExperienceTracker(ExperienceRepository(conn))
    tracker.record(seeded_session, "Docker", "Built image", ExperienceState.INTRODUCED)
    tracker.record(seeded_session, "Docker", "Built image", ExperienceState.PRACTICED)

    summary = tracker.summary(seeded_session)
    assert len(summary["Docker"]) == 1
    assert summary["Docker"][0].state == ExperienceState.PRACTICED
