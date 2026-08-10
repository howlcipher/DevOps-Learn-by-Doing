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

from dataclasses import dataclass, field, replace
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

_STALE_POINTER_NOTICE = (
    "This project's content changed since your last session, so you have been "
    "moved to the start of the nearest module."
)


@dataclass(frozen=True)
class TurnResult:
    session: LearningSession
    heading: str
    blocks: tuple[ContentBlock, ...] = field(default_factory=tuple)
    menu: tuple[MenuOption, ...] = _DEFAULT_MENU
    status_message: str | None = None
    prediction: PredictionPrompt | None = None
    is_terminal: bool = False
    question_keys: tuple[str, ...] = ()
    """Option keys of a check question displayed on this turn, if any.

    The session loop resolves a single-letter input against these before the
    menu, so a task offering both cannot make one of them unreachable.
    """


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
        repaired = self._repair_stale_pointer(session)
        if repaired is not None:
            turn = self.resume(repaired, level=level, depth=depth)
            return replace(turn, status_message=_STALE_POINTER_NOTICE)
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
            question_keys=self._pending_question_keys(session, task, arranged.proactive),
        )

    def answer_question(self, session: LearningSession, *, chosen_key: str) -> TurnResult:
        task = self._current_task(session)
        if task is None:
            return self._no_task_turn(session, "There is no question on this screen.")
        question = self._find_question(task)
        if question is None:
            return TurnResult(
                session=session,
                heading=task.title,
                menu=self._menu_for_task(task),
                status_message="This task has no check question.",
            )
        if chosen_key not in {option.key for option in question.options}:
            return TurnResult(
                session=session,
                heading=task.title,
                menu=self._menu_for_task(task),
                status_message=f"'{chosen_key}' is not one of the offered answers.",
                question_keys=self._pending_question_keys(session, task),
            )
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
        return TurnResult(
            session=session,
            heading=task.title,
            menu=self._menu_for_task(task),
            status_message=assessment.feedback,
        )

    def request_hint(self, session: LearningSession) -> TurnResult:
        task = self._current_task(session)
        if task is None:
            return self._no_task_turn(
                session, "There is no task on this screen to hint on. Type 'continue' to move on."
            )

        scenario = scenario_for_task(task.id) if is_troubleshooting_task(task.id) else None
        if scenario is not None:
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
        return TurnResult(
            session=session,
            heading=task.title,
            menu=self._menu_for_task(task),
            status_message=message,
            question_keys=self._pending_question_keys(session, task),
        )

    def submit_diagnosis(self, session: LearningSession, *, diagnosis_key: str) -> TurnResult:
        task = self._current_task(session)
        if task is None:
            return self._no_task_turn(session, "There is no failure to diagnose on this screen.")
        scenario = scenario_for_task(task.id)
        if scenario is None:
            return TurnResult(
                session=session,
                heading=task.title,
                menu=self._menu_for_task(task),
                status_message="This task is not a troubleshooting exercise.",
            )
        attempt = self._attempt_tracker.get_or_start(
            session_id=self._require_id(session), learner_id=session.learner_id, task_id=task.id
        )
        outcome = self._troubleshooting.submit_diagnosis(attempt, scenario, diagnosis_key)
        if outcome.is_correct:
            assert outcome.resolution is not None
            message = f"Correct. {outcome.resolution.explanation}"
        else:
            message = "That doesn't match the evidence. Try again, or request a hint."
        return TurnResult(
            session=session,
            heading=task.title,
            menu=self._menu_for_task(task),
            status_message=message,
        )

    def attempt_task(self, session: LearningSession, *, learner_response: str) -> TurnResult:
        task = self._current_task(session)
        if task is None:
            return self._no_task_turn(session, "There is no task on this screen to attempt.")
        assessment = self._assessment.assess_open_response(task, learner_response)
        message = assessment.feedback
        if task.prediction is not None:
            message += f"\n\nWhat actually happens: {task.prediction.outcome_summary}"
        return TurnResult(
            session=session,
            heading=task.title,
            menu=self._menu_for_task(task),
            status_message=message,
            question_keys=self._pending_question_keys(session, task),
        )

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
        repaired = self._repair_stale_pointer(session)
        if repaired is not None:
            turn = self.resume(repaired, level=level, depth=depth)
            return replace(turn, status_message=_STALE_POINTER_NOTICE)
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

    def _menu_for_task(self, task: Task) -> tuple[MenuOption, ...]:
        """A task's menu regardless of depth; NEXT_STEP_MENU blocks are always included."""
        return self._extract_menu(task.content)

    def _pending_question_keys(
        self,
        session: LearningSession,
        task: Task,
        displayed_blocks: tuple[ContentBlock, ...] | None = None,
    ) -> tuple[str, ...]:
        """Answer keys the next turn should route to the question rather than the menu.

        Empty once the question has been answered in this session, so a task whose
        question and menu share keys hands them back to the menu afterwards.
        """
        question = self._find_question(task)
        if question is None:
            return ()
        if displayed_blocks is not None and not any(
            block.kind == ContentBlockKind.CHECK_QUESTION for block in displayed_blocks
        ):
            return ()
        if session.id is not None and self._journal.has_recorded(
            session_id=session.id,
            event_type=LearningEventType.QUESTION_ANSWERED,
            task_id=task.id,
        ):
            return ()
        return tuple(option.key for option in question.options)

    def _current_task(self, session: LearningSession) -> Task | None:
        return self._curriculum.find_task(session.current_task_id)

    def _no_task_turn(self, session: LearningSession, message: str) -> TurnResult:
        return TurnResult(session=session, heading="NO ACTIVE TASK", status_message=message)

    def _repair_stale_pointer(self, session: LearningSession) -> LearningSession | None:
        """Re-anchor a saved pointer that current curriculum content no longer contains.

        Returns the repaired session, or None when the pointer is already valid.
        Content ids are persisted, so renaming or removing a module, lesson or
        task would otherwise leave every in-flight session unresumable.
        """
        module = self._curriculum.find_module(session.current_module_id)
        lesson = self._curriculum.find_lesson(session.current_lesson_id)
        task = self._curriculum.find_task(session.current_task_id)

        lesson_belongs = lesson is not None and module is not None and lesson in module.lessons
        task_missing = session.current_task_id is not None and task is None
        task_belongs = task is None or (lesson is not None and task in lesson.tasks)
        if module is not None and lesson_belongs and not task_missing and task_belongs:
            return None

        anchor_module = module if module is not None else self._curriculum.first_module()
        anchor_lesson = (
            lesson if lesson is not None and lesson in anchor_module.lessons
            else anchor_module.lessons[0]
        )
        anchor_task = anchor_lesson.tasks[0] if anchor_lesson.tasks else None
        return self._session.advance_pointer(
            session,
            module_id=anchor_module.id,
            lesson_id=anchor_lesson.id,
            task_id=anchor_task.id if anchor_task is not None else None,
        )

    def _find_question(self, task: Task) -> ComprehensionQuestion | None:
        for block in task.content:
            if block.kind == ContentBlockKind.CHECK_QUESTION and block.question is not None:
                return block.question
        return None

    def _require_id(self, session: LearningSession) -> int:
        assert session.id is not None
        return session.id
