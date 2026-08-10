"""Evaluates learner answers: deterministic for multiple choice, LLM-assisted
for open-ended reflection (predictions, explain-in-your-own-words).

A correct comprehension check only ever reaches INTRODUCED via CompetencyService,
matching ADR 0008: a quiz answer is not the same thing as demonstrating a skill.
"""

from __future__ import annotations

from datetime import datetime

from devops_learn.ai.provider import LLMProvider
from devops_learn.competencies.service import CompetencyService
from devops_learn.domain.content import ComprehensionQuestion
from devops_learn.domain.curriculum_models import Task
from devops_learn.domain.tutor_models import Assessment


class AssessmentService:
    def __init__(self, llm_provider: LLMProvider, competency_service: CompetencyService) -> None:
        self._llm_provider = llm_provider
        self._competency_service = competency_service

    def assess_choice_answer(
        self,
        *,
        session_id: int,
        learner_id: int,
        task: Task,
        question: ComprehensionQuestion,
        chosen_key: str,
        triggering_event_id: int,
        occurred_at: datetime,
    ) -> Assessment:
        is_correct = chosen_key.strip().upper() == question.correct_key.upper()
        feedback = (
            question.explanation_correct if is_correct else question.explanation_incorrect
        )
        if is_correct and task.competency_codes:
            self._competency_service.record_content_viewed(
                session_id=session_id,
                learner_id=learner_id,
                codes=task.competency_codes,
                triggering_event_id=triggering_event_id,
                occurred_at=occurred_at,
            )
        return Assessment(task_id=task.id, feedback=feedback, is_correct=is_correct)

    def assess_open_response(self, task: Task, learner_response: str) -> Assessment:
        return self._llm_provider.assess_open_response(task, learner_response)
