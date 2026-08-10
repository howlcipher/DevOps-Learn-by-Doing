import sqlite3

from devops_learn.competencies.service import CompetencyService
from devops_learn.domain.enums import CompetencyCode, CompetencyState
from devops_learn.learning.journal import LearningJournal
from devops_learn.learning.persistence.repositories.competency_repository import (
    CompetencyRepository,
)
from devops_learn.learning.persistence.repositories.event_repository import EventRepository
from devops_learn.learning.persistence.repositories.task_attempt_repository import (
    TaskAttemptRepository,
)
from devops_learn.troubleshooting.menu import build_inspection_menu, resolve_source
from devops_learn.troubleshooting.scenarios import build_container_wont_start_scenario
from devops_learn.troubleshooting.service import TroubleshootingService

TASK_ID = "troubleshoot_container_wont_start"


def _service(conn: sqlite3.Connection) -> TroubleshootingService:
    journal = LearningJournal(EventRepository(conn))
    competency_service = CompetencyService(CompetencyRepository(conn), journal)
    return TroubleshootingService(TaskAttemptRepository(conn), journal, competency_service)


def test_learner_can_inspect_evidence_and_reach_the_correct_diagnosis_unhinted(
    conn: sqlite3.Connection, seeded_session: tuple[int, int]
) -> None:
    learner_id, session_id = seeded_session
    scenario = build_container_wont_start_scenario()
    service = _service(conn)

    attempt = service.start(session_id=session_id, learner_id=learner_id, task_id=TASK_ID)

    step = scenario.steps[0]
    menu = build_inspection_menu(step)
    assert len(menu) == 4
    logs = resolve_source(step, "B")
    assert logs.id == "container_logs"
    assert logs.is_relevant is True

    outcome = service.submit_diagnosis(attempt, scenario, "missing_port_env_var")
    assert outcome.is_correct is True
    assert outcome.hints_used == 0
    assert outcome.resolution is not None
    assert "PORT" in outcome.resolution.explanation

    states = CompetencyRepository(conn).list_states(learner_id)
    docker_state = next(s for s in states if s.code == CompetencyCode.DOCKER)
    assert docker_state.state == CompetencyState.DEMONSTRATED


def test_hints_escalate_in_order_and_run_out(
    conn: sqlite3.Connection, seeded_session: tuple[int, int]
) -> None:
    learner_id, session_id = seeded_session
    scenario = build_container_wont_start_scenario()
    service = _service(conn)
    attempt = service.start(session_id=session_id, learner_id=learner_id, task_id=TASK_ID)

    hint1 = service.request_hint(attempt, scenario)
    hint2 = service.request_hint(attempt, scenario)
    hint3 = service.request_hint(attempt, scenario)
    hint4 = service.request_hint(attempt, scenario)

    assert hint1 is not None and hint1.level == 1
    assert hint2 is not None and hint2.level == 2
    assert hint3 is not None and hint3.level == 3
    assert hint4 is None  # hints exhausted; full explanation logic takes over elsewhere


def test_wrong_diagnosis_is_tracked_and_learner_can_retry(
    conn: sqlite3.Connection, seeded_session: tuple[int, int]
) -> None:
    learner_id, session_id = seeded_session
    scenario = build_container_wont_start_scenario()
    service = _service(conn)
    attempt = service.start(session_id=session_id, learner_id=learner_id, task_id=TASK_ID)

    first = service.submit_diagnosis(attempt, scenario, "corrupted_image")
    assert first.is_correct is False
    assert first.resolution is None

    second = service.submit_diagnosis(attempt, scenario, "missing_port_env_var")
    assert second.is_correct is True
