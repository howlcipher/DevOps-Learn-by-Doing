import sqlite3
from datetime import datetime, timezone

from devops_learn.ai.mock_provider import MockLLMProvider
from devops_learn.assessments.service import AssessmentService
from devops_learn.competencies.service import CompetencyService
from devops_learn.curriculum.content_library import build_api_platform_project
from devops_learn.domain.enums import CompetencyState, ContentBlockKind
from devops_learn.learning.journal import LearningJournal
from devops_learn.learning.persistence.repositories.competency_repository import (
    CompetencyRepository,
)
from devops_learn.domain.enums import LearningEventType
from devops_learn.domain.event_models import LearningEvent
from devops_learn.learning.persistence.repositories.event_repository import EventRepository

NOW = datetime(2026, 8, 9, 12, 0, 0, tzinfo=timezone.utc)


def _seed_event(conn: sqlite3.Connection, *, session_id: int, learner_id: int) -> int:
    event = EventRepository(conn).append(
        LearningEvent(
            session_id=session_id,
            learner_id=learner_id,
            sequence_no=1,
            event_type=LearningEventType.QUESTION_ANSWERED,
            occurred_at=NOW,
        )
    )
    assert event.id is not None
    return event.id


def _task_and_question():
    project = build_api_platform_project()
    task = project.modules[0].lessons[0].tasks[0]
    block = next(b for b in task.content if b.kind == ContentBlockKind.CHECK_QUESTION)
    assert block.question is not None
    return task, block.question


def _service(conn: sqlite3.Connection) -> AssessmentService:
    journal = LearningJournal(EventRepository(conn))
    competency_service = CompetencyService(CompetencyRepository(conn), journal)
    return AssessmentService(MockLLMProvider(), competency_service)


def test_correct_choice_answer_advances_competency_to_introduced_only(
    conn: sqlite3.Connection, seeded_session: tuple[int, int]
) -> None:
    learner_id, session_id = seeded_session
    event_id = _seed_event(conn, session_id=session_id, learner_id=learner_id)
    task, question = _task_and_question()
    service = _service(conn)

    assessment = service.assess_choice_answer(
        session_id=session_id,
        learner_id=learner_id,
        task=task,
        question=question,
        chosen_key=question.correct_key,
        triggering_event_id=event_id,
        occurred_at=NOW,
    )

    assert assessment.is_correct is True
    states = CompetencyRepository(conn).list_states(learner_id)
    assert states
    assert all(s.state == CompetencyState.INTRODUCED for s in states)


def test_wrong_choice_answer_advances_nothing(
    conn: sqlite3.Connection, seeded_session: tuple[int, int]
) -> None:
    learner_id, session_id = seeded_session
    task, question = _task_and_question()
    wrong_key = next(o.key for o in question.options if o.key != question.correct_key)
    service = _service(conn)

    assessment = service.assess_choice_answer(
        session_id=session_id,
        learner_id=learner_id,
        task=task,
        question=question,
        chosen_key=wrong_key,
        triggering_event_id=1,
        occurred_at=NOW,
    )

    assert assessment.is_correct is False
    assert CompetencyRepository(conn).list_states(learner_id) == []


def test_open_response_is_delegated_to_the_llm_provider_and_is_ungraded(
    conn: sqlite3.Connection,
) -> None:
    task, _ = _task_and_question()
    service = _service(conn)
    assessment = service.assess_open_response(task, "It will cache the layer.")
    assert assessment.is_correct is None
