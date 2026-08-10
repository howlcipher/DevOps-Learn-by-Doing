import sqlite3

from devops_learn.competencies.service import CompetencyService
from devops_learn.domain.enums import CompetencyState
from devops_learn.learning.journal import LearningJournal
from devops_learn.learning.persistence.repositories.competency_repository import (
    CompetencyRepository,
)
from devops_learn.learning.persistence.repositories.event_repository import EventRepository
from devops_learn.learning.persistence.repositories.task_attempt_repository import (
    TaskAttemptRepository,
)
from devops_learn.troubleshooting.scenarios import build_container_wont_start_scenario
from devops_learn.troubleshooting.service import TroubleshootingService

TASK_ID = "troubleshoot_container_wont_start"


def _service(conn: sqlite3.Connection) -> TroubleshootingService:
    journal = LearningJournal(EventRepository(conn))
    competency_service = CompetencyService(CompetencyRepository(conn), journal)
    return TroubleshootingService(TaskAttemptRepository(conn), journal, competency_service)


def test_a_wrong_diagnosis_alone_never_advances_any_competency(
    conn: sqlite3.Connection, seeded_session: tuple[int, int]
) -> None:
    learner_id, session_id = seeded_session
    scenario = build_container_wont_start_scenario()
    service = _service(conn)
    attempt = service.start(session_id=session_id, learner_id=learner_id, task_id=TASK_ID)

    for wrong_key in ("corrupted_image", "dns_failure", "terraform_drift"):
        outcome = service.submit_diagnosis(attempt, scenario, wrong_key)
        assert outcome.is_correct is False

    states = CompetencyRepository(conn).list_states(learner_id)
    assert states == []  # no diagnosis reached SUCCESS, so no competency row was ever written


def test_only_inspecting_evidence_without_ever_diagnosing_advances_nothing(
    conn: sqlite3.Connection, seeded_session: tuple[int, int]
) -> None:
    """Mirrors ADR 0008: content exposure/investigation alone is not demonstration."""
    learner_id, session_id = seeded_session
    service = _service(conn)
    service.start(session_id=session_id, learner_id=learner_id, task_id=TASK_ID)

    states = CompetencyRepository(conn).list_states(learner_id)
    assert states == []


def test_reaching_correct_diagnosis_only_after_using_every_hint_caps_at_guided(
    conn: sqlite3.Connection, seeded_session: tuple[int, int]
) -> None:
    learner_id, session_id = seeded_session
    scenario = build_container_wont_start_scenario()
    service = _service(conn)
    attempt = service.start(session_id=session_id, learner_id=learner_id, task_id=TASK_ID)

    for _ in scenario.hints:
        service.request_hint(attempt, scenario)

    outcome = service.submit_diagnosis(attempt, scenario, "missing_port_env_var")
    assert outcome.is_correct is True

    states = CompetencyRepository(conn).list_states(learner_id)
    troubleshooting_state = next(
        s for s in states if s.code.value == "troubleshooting"
    )
    assert troubleshooting_state.state == CompetencyState.GUIDED
