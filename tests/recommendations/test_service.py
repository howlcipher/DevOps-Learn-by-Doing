import sqlite3
from datetime import datetime, timezone

from devops_learn.ai.mock_provider import MockLLMProvider
from devops_learn.competencies.service import CompetencyService
from devops_learn.curriculum.content_library import build_api_platform_project
from devops_learn.curriculum.service import CurriculumService
from devops_learn.domain.competency_models import LearnerCompetency
from devops_learn.domain.enums import CompetencyState
from devops_learn.learning.journal import LearningJournal
from devops_learn.learning.persistence.repositories.competency_repository import (
    CompetencyRepository,
)
from devops_learn.learning.persistence.repositories.event_repository import EventRepository
from devops_learn.recommendations.service import RecommendationService

NOW = datetime(2026, 8, 9, 12, 0, 0, tzinfo=timezone.utc)


def _service(conn: sqlite3.Connection) -> RecommendationService:
    journal = LearningJournal(EventRepository(conn))
    competency_service = CompetencyService(CompetencyRepository(conn), journal)
    return RecommendationService(MockLLMProvider(), CurriculumService(), competency_service)


def test_recommend_for_task_reflects_prior_demonstration(
    conn: sqlite3.Connection, seeded_session: tuple[int, int]
) -> None:
    learner_id, _ = seeded_session
    project = build_api_platform_project()
    task = project.modules[1].lessons[0].tasks[0]  # task_write_dockerfile -> DOCKER

    for code in task.competency_codes:
        CompetencyRepository(conn).upsert_state(
            LearnerCompetency(
                learner_id=learner_id, code=code, state=CompetencyState.DEMONSTRATED,
                updated_at=NOW,
            )
        )

    recommendation = _service(conn).recommend_for_task(task, learner_id=learner_id)
    assert "already demonstrated" in recommendation.learning_value


def test_recommend_next_step_at_the_final_module_suggests_architecture_review(
    conn: sqlite3.Connection,
) -> None:
    curriculum = CurriculumService()
    last_module_id = curriculum.project.modules[-1].id
    recommendation = _service(conn).recommend_next_step(
        learner_id=1, current_module_id=last_module_id
    )
    assert "architecture" in recommendation.recommendation.lower()
    assert "review" in recommendation.recommendation.lower()


def test_recommend_next_step_mid_project_suggests_the_next_module(
    conn: sqlite3.Connection,
) -> None:
    curriculum = CurriculumService()
    first_module_id = curriculum.project.modules[0].id
    second_module = curriculum.next_module(first_module_id)
    assert second_module is not None

    recommendation = _service(conn).recommend_next_step(
        learner_id=1, current_module_id=first_module_id
    )
    assert second_module.title in recommendation.title
