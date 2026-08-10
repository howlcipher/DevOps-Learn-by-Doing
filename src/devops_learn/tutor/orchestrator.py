"""TutorOrchestrator: the single modular-monolith coordinator (see ADR 0002).

Wires CurriculumService, AssessmentService, RecommendationService,
CompetencyService, TroubleshootingService, ProjectService, ToolService, and
LLMProvider (the architecture named in the product spec), plus SessionService,
LearningJournal, and AttemptTracker/TaskAttemptRepository, which the CLI-facing
begin_project/resume/advance/request_hint methods need for session lifecycle
and generic hint tracking. See docs/adr/0002-modular-monolith.md for why this
extension was made and why it stays a thin dispatcher rather than growing
business logic of its own.

Each public method is stateless across calls: it takes the current
LearningSession explicitly and returns a TurnResult carrying the (possibly
updated) session, so the CLI session loop threads state through return values
rather than the orchestrator holding any of its own.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping

from devops_learn.ai.provider import LLMProvider
from devops_learn.assessments.service import AssessmentService
from devops_learn.competencies.service import CompetencyService
from devops_learn.curriculum.service import CurriculumService
from devops_learn.domain.content import (
    ComprehensionQuestion,
    ContentBlock,
    MenuOption,
    PredictionPrompt,
)
from devops_learn.domain.curriculum_models import Task
from devops_learn.domain.enums import (
    AssistanceLevel,
    ContentBlockKind,
    ExplanationDepth,
    LearningEventType,
)
from devops_learn.domain.learner_models import LearningSession
from devops_learn.learning.attempt_tracker import AttemptTracker
from devops_learn.learning.journal import LearningJournal
from devops_learn.learning.persistence.repositories.task_attempt_repository import (
    TaskAttemptRepository,
)
from devops_learn.learning.session_service import SessionService
from devops_learn.projects.service import ProjectService
from devops_learn.recommendations.service import RecommendationService
from devops_learn.tools.service import ToolService
from devops_learn.troubleshooting.service import TroubleshootingService
from devops_learn.workflows.start_flow import start_project
from devops_learn.workflows.troubleshooting_flow import is_troubleshooting_task, scenario_for_task

_DEFAULT_MENU = (MenuOption("C", "Continue"),)


@dataclass(frozen=True)
class TurnResult:
    session: LearningSession
    heading: str
    blocks: tuple[ContentBlock, ...] = field(default_factory=tuple)
    menu: tuple[MenuOption, ...] = _DEFAULT_MENU
    status_message: str | None = None
    prediction: PredictionPrompt | None = None
    is_terminal: bool = False


class TutorOrchestrator:
    def __init__(
        self,
        curriculum: CurriculumService,
        assessment: AssessmentService,
        recommendation: RecommendationService,
        competency: CompetencyService,
        troubleshooting: TroubleshootingService,
        project: ProjectService,
        tool: ToolService,
        llm: LLMProvider,
        session: SessionService,
        journal: LearningJournal,
        task_attempt_repository: TaskAttemptRepository,
    ) -> None:
        self._curriculum = curriculum
        self._assessment = assessment
        self._recommendation = recommendation
        self._competency = competency
        self._troubleshooting = troubleshooting
        self._project = project
        self._tool = tool
        self._llm = llm
        self._session = session
        self._journal = journal
        self._attempt_tracker = AttemptTracker(task_attempt_repository, journal)
        self._task_attempt_repository = task_attempt_repository

    def begin_project(
        self,
        *,
        learner_id: int,
        project_id: str,
        simulation_mode: bool,
        level: AssistanceLevel,
        depth: ExplanationDepth,
    ) -> TurnResult:
        result = start_project(
            learner_id=learner_id,
            project_id=project_id,
            simulation_mode=simulation_mode,
            session_service=self._session,
            curriculum_service=self._curriculum,
            journal=self._journal,
        )
        if result.session.current_task_id is None:
            arranged = self._curriculum.render_task_content(
                Task(id="", title="", goal="", content=result.lesson.content, competency_codes=()),
                level,
                depth,
            )
            return TurnResult(
                session=result.session,
                heading=f"MODULE: {result.module.title}",
                blocks=arranged.proactive,
            )
        return self.render_current_task(result.session, level=level, depth=depth)

    def resume(
        self, session: LearningSession, *, level: AssistanceLevel, depth: ExplanationDepth
    ) -> TurnResult:
        if session.current_task_id is None:
            assert session.current_lesson_id is not None
            lesson = self._curriculum.lesson(session.current_lesson_id)
            module = self._curriculum.module_for_lesson(session.current_lesson_id)
            arranged = self._curriculum.render_task_content(
                Task(id="", title="", goal="", content=lesson.content, competency_codes=()),
                level,
                depth,
            )
            return TurnResult(
                session=session, heading=f"MODULE: {module.title}", blocks=arranged.proactive
            )
        return self.render_current_task(session, level=level, depth=depth)

    def render_current_task(
        self, session: LearningSession, *, level: AssistanceLevel, depth: ExplanationDepth
    ) -> TurnResult:
        assert session.current_task_id is not None
        task = self._curriculum.task(session.current_task_id)
        module = (
            self._curriculum.module_for_lesson(session.current_lesson_id)
            if session.current_lesson_id
            else None
        )
        arranged = self._curriculum.render_task_content(task, level, depth)
        menu = self._extract_menu(arranged.proactive)
        heading = f"{module.title}: {task.title}" if module else task.title
        return TurnResult(
            session=session,
            heading=heading,
            blocks=arranged.proactive,
            menu=menu,
            prediction=task.prediction,
        )

    def answer_question(self, session: LearningSession, *, chosen_key: str) -> TurnResult:
        assert session.current_task_id is not None
        task = self._curriculum.task(session.current_task_id)
        question = self._find_question(task)
        now = datetime.now(timezone.utc)
        event = self._journal.record(
            session_id=self._require_id(session),
            learner_id=session.learner_id,
            event_type=LearningEventType.QUESTION_ANSWERED,
            occurred_at=now,
            task_id=task.id,
            payload={"chosen_key": chosen_key},
        )
        assert event.id is not None
        assessment = self._assessment.assess_choice_answer(
            session_id=self._require_id(session),
            learner_id=session.learner_id,
            task=task,
            question=question,
            chosen_key=chosen_key,
            triggering_event_id=event.id,
            occurred_at=now,
        )
        return TurnResult(session=session, heading=task.title, status_message=assessment.feedback)

    def request_hint(self, session: LearningSession) -> TurnResult:
        assert session.current_task_id is not None
        task = self._curriculum.task(session.current_task_id)

        if is_troubleshooting_task(task.id):
            scenario = scenario_for_task(task.id)
            assert scenario is not None
            attempt = self._attempt_tracker.get_or_start(
                session_id=self._require_id(session), learner_id=session.learner_id, task_id=task.id
            )
            hint = self._troubleshooting.request_hint(attempt, scenario)
        else:
            attempt = self._attempt_tracker.get_or_start(
                session_id=self._require_id(session), learner_id=session.learner_id, task_id=task.id
            )
            hint = self._attempt_tracker.request_hint(attempt, task.hints)

        if hint is None:
            message = "No more hints available. Ask for the full explanation if you're stuck."
        else:
            message = f"HINT {hint.level}: {hint.text}"
        return TurnResult(session=session, heading=task.title, status_message=message)

    def submit_diagnosis(self, session: LearningSession, *, diagnosis_key: str) -> TurnResult:
        assert session.current_task_id is not None
        task = self._curriculum.task(session.current_task_id)
        scenario = scenario_for_task(task.id)
        assert scenario is not None, f"'{task.id}' is not a troubleshooting task"
        attempt = self._attempt_tracker.get_or_start(
            session_id=self._require_id(session), learner_id=session.learner_id, task_id=task.id
        )
        outcome = self._troubleshooting.submit_diagnosis(attempt, scenario, diagnosis_key)
        if outcome.is_correct:
            assert outcome.resolution is not None
            message = f"Correct. {outcome.resolution.explanation}"
        else:
            message = "That doesn't match the evidence. Try again, or request a hint."
        return TurnResult(session=session, heading=task.title, status_message=message)

    def attempt_task(self, session: LearningSession, *, learner_response: str) -> TurnResult:
        assert session.current_task_id is not None
        task = self._curriculum.task(session.current_task_id)
        assessment = self._assessment.assess_open_response(task, learner_response)
        message = assessment.feedback
        if task.prediction is not None:
            message += f"\n\nWhat actually happens: {task.prediction.outcome_summary}"
        return TurnResult(session=session, heading=task.title, status_message=message)

    def run_tool(
        self,
        session: LearningSession,
        *,
        tool_name: str,
        operation: str,
        params: Mapping[str, Any] | None = None,
        dry_run: bool = False,
    ) -> TurnResult:
        result = self._tool.invoke(tool_name, operation, params, dry_run=dry_run)
        return TurnResult(
            session=session, heading=f"{tool_name} {operation}", status_message=result.summary
        )

    def explain(
        self,
        session: LearningSession,
        topic: str,
        *,
        level: AssistanceLevel,
        depth: ExplanationDepth,
    ) -> TurnResult:
        explanation = self._llm.explain_topic(topic, level=level, depth=depth)
        return TurnResult(
            session=session, heading=explanation.title, status_message=explanation.body
        )

    def advance(
        self, session: LearningSession, *, level: AssistanceLevel, depth: ExplanationDepth
    ) -> TurnResult:
        assert session.current_module_id is not None and session.current_lesson_id is not None
        old_module_id = session.current_module_id
        now = datetime.now(timezone.utc)

        result = self._curriculum.next_task(
            session.current_module_id, session.current_lesson_id, session.current_task_id
        )
        if result is None:
            self._journal.record(
                session_id=self._require_id(session),
                learner_id=session.learner_id,
                event_type=LearningEventType.MODULE_COMPLETED,
                occurred_at=now,
                module_id=old_module_id,
            )
            completed = self._session.complete_session(session)
            return TurnResult(
                session=completed,
                heading="PROJECT COMPLETE",
                status_message="You have completed every module in this project.",
                is_terminal=True,
            )

        module, lesson, task = result
        if module.id != old_module_id:
            self._journal.record(
                session_id=self._require_id(session),
                learner_id=session.learner_id,
                event_type=LearningEventType.MODULE_COMPLETED,
                occurred_at=now,
                module_id=old_module_id,
            )

        updated_session = self._session.advance_pointer(
            session, module_id=module.id, lesson_id=lesson.id, task_id=task.id if task else None
        )
        self._journal.record(
            session_id=self._require_id(updated_session),
            learner_id=session.learner_id,
            event_type=LearningEventType.LESSON_STARTED,
            occurred_at=now,
            module_id=module.id,
            lesson_id=lesson.id,
        )

        if task is None:
            arranged = self._curriculum.render_task_content(
                Task(id="", title="", goal="", content=lesson.content, competency_codes=()),
                level,
                depth,
            )
            return TurnResult(
                session=updated_session,
                heading=f"MODULE: {module.title}",
                blocks=arranged.proactive,
            )
        return self.render_current_task(updated_session, level=level, depth=depth)

    def _extract_menu(self, blocks: tuple[ContentBlock, ...]) -> tuple[MenuOption, ...]:
        for block in blocks:
            if block.kind == ContentBlockKind.NEXT_STEP_MENU and block.menu_options:
                return block.menu_options
        return _DEFAULT_MENU

    def _find_question(self, task: Task) -> ComprehensionQuestion:
        for block in task.content:
            if block.kind == ContentBlockKind.CHECK_QUESTION and block.question is not None:
                return block.question
        raise ValueError(f"Task '{task.id}' has no check question")

    def _require_id(self, session: LearningSession) -> int:
        assert session.id is not None
        return session.id
