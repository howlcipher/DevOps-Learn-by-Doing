"""Produces structured Recommendations, adjusted by what the learner has already
demonstrated so the same decision point does not read as equally novel forever."""

from __future__ import annotations

import dataclasses

from devops_learn.ai.provider import LLMProvider
from devops_learn.competencies.service import CompetencyService
from devops_learn.curriculum.service import CurriculumService
from devops_learn.domain.curriculum_models import Task
from devops_learn.domain.enums import CompetencyState
from devops_learn.domain.tutor_models import Recommendation


class RecommendationService:
    def __init__(
        self,
        llm_provider: LLMProvider,
        curriculum_service: CurriculumService,
        competency_service: CompetencyService,
    ) -> None:
        self._llm_provider = llm_provider
        self._curriculum_service = curriculum_service
        self._competency_service = competency_service

    def recommend_for_task(self, task: Task, *, learner_id: int) -> Recommendation:
        context = f"Task: {task.title}. Goal: {task.goal}."
        recommendation = self._llm_provider.recommend(task.title, context)

        if task.competency_codes and self._already_demonstrated_all(learner_id, task):
            recommendation = dataclasses.replace(
                recommendation,
                learning_value="Low: you have already demonstrated this competency.",
            )
        return recommendation

    def recommend_next_step(self, *, learner_id: int, current_module_id: str) -> Recommendation:
        next_module = self._curriculum_service.next_module(current_module_id)
        if next_module is None:
            return Recommendation(
                title="Project complete",
                recommendation=(
                    "Review the architecture end to end before starting a new project."
                ),
                reason="You have completed every module in this project.",
                learning_value="High: architecture review consolidates everything you built.",
            )
        context = f"The learner just finished module {current_module_id}."
        return self._llm_provider.recommend(f"Start {next_module.title}", context)

    def _already_demonstrated_all(self, learner_id: int, task: Task) -> bool:
        states = {s.code: s.state for s in self._competency_service.list_states(learner_id)}
        return all(
            states.get(code, CompetencyState.NOT_STARTED) == CompetencyState.DEMONSTRATED
            for code in task.competency_codes
        )
