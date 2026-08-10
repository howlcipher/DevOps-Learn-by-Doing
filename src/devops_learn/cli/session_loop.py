"""The interactive REPL for `devops-learn start` / `resume`.

Dispatches raw learner input to one TutorOrchestrator method per turn. Menu
selections are interpreted by matching the currently offered MenuOption's
label (see _handle_menu_selection) rather than hardcoding per-task branches,
so new curriculum content stays wired up without new session_loop code.
"""

from __future__ import annotations

from devops_learn.cli.presenters import render_turn
from devops_learn.domain.content import MenuOption
from devops_learn.domain.curriculum_models import Task
from devops_learn.domain.enums import AssistanceLevel, ExplanationDepth
from devops_learn.domain.learner_models import LearningSession
from devops_learn.tutor.bootstrap import Platform
from devops_learn.tutor.orchestrator import TurnResult
from devops_learn.workflows.troubleshooting_flow import is_troubleshooting_task, scenario_for_task
from devops_learn.troubleshooting.menu import MenuKeyError, resolve_diagnosis, resolve_source

_QUIT_COMMANDS = {"quit", "exit"}


def run_interactive_session(
    platform: Platform,
    learner_id: int,
    *,
    level: AssistanceLevel,
    depth: ExplanationDepth,
    simulation_mode: bool = True,
) -> None:
    turn = platform.orchestrator.begin_project(
        learner_id=learner_id,
        project_id=platform.curriculum_service.project.id,
        simulation_mode=simulation_mode,
        level=level,
        depth=depth,
    )
    _loop(platform, turn, level=level, depth=depth)


def resume_interactive_session(
    platform: Platform,
    session: LearningSession,
    *,
    level: AssistanceLevel,
    depth: ExplanationDepth,
) -> None:
    turn = platform.orchestrator.resume(session, level=level, depth=depth)
    _loop(platform, turn, level=level, depth=depth)


def _loop(
    platform: Platform, turn: TurnResult, *, level: AssistanceLevel, depth: ExplanationDepth
) -> None:
    render_turn(turn)
    while not turn.is_terminal:
        try:
            raw = input("> ")
        except EOFError:
            break
        if raw.strip().lower() in _QUIT_COMMANDS:
            print("Progress is saved. Run 'devops-learn resume' to continue later.")
            break
        turn = _dispatch(platform, turn, raw, level=level, depth=depth)
        render_turn(turn)


def _dispatch(
    platform: Platform,
    turn: TurnResult,
    raw: str,
    *,
    level: AssistanceLevel,
    depth: ExplanationDepth,
) -> TurnResult:
    text = raw.strip()
    lower = text.lower()
    session = turn.session
    orchestrator = platform.orchestrator

    if lower == "hint":
        return orchestrator.request_hint(session)
    if lower in ("advance", "continue", "next"):
        return orchestrator.advance(session, level=level, depth=depth)
    if lower.startswith("explain"):
        topic = text[len("explain"):].strip() or turn.heading
        return orchestrator.explain(session, topic, level=level, depth=depth)

    task = (
        platform.curriculum_service.task(session.current_task_id)
        if session.current_task_id
        else None
    )

    if task is not None and is_troubleshooting_task(task.id):
        scenario = scenario_for_task(task.id)
        assert scenario is not None
        if lower.startswith("diagnose"):
            key = text[len("diagnose"):].strip().upper()
            try:
                diagnosis = resolve_diagnosis(scenario, key)
            except MenuKeyError:
                return TurnResult(
                    session=session,
                    heading=turn.heading,
                    menu=turn.menu,
                    status_message="Unrecognized diagnosis letter. Try one shown above.",
                )
            return orchestrator.submit_diagnosis(session, diagnosis_key=diagnosis.key)
        if len(text) == 1 and text.isalpha():
            try:
                source = resolve_source(scenario.steps[0], text)
            except MenuKeyError:
                pass
            else:
                return TurnResult(
                    session=session,
                    heading=turn.heading,
                    menu=turn.menu,
                    status_message=f"{source.label}: {source.evidence_text}",
                )

    if task is not None and len(text) == 1 and text.isalpha():
        question_keys = _check_question_keys(task)
        if text.upper() in question_keys:
            return orchestrator.answer_question(session, chosen_key=text.upper())

    if len(text) == 1 and text.isalpha():
        matching = next((o for o in turn.menu if o.key == text.upper()), None)
        if matching is not None:
            return _handle_menu_selection(
                platform, session, task, matching, level=level, depth=depth
            )

    if task is not None and task.prediction is not None:
        return orchestrator.attempt_task(session, learner_response=text)

    return TurnResult(
        session=session,
        heading=turn.heading,
        menu=turn.menu,
        status_message="I didn't understand that. Try 'hint', 'advance', or a lettered option.",
    )


def _check_question_keys(task: Task) -> set[str]:
    for block in task.content:
        if block.question is not None:
            return {o.key for o in block.question.options}
    return set()


def _handle_menu_selection(
    platform: Platform,
    session: LearningSession,
    task: Task | None,
    option: MenuOption,
    *,
    level: AssistanceLevel,
    depth: ExplanationDepth,
) -> TurnResult:
    label = option.label.lower()
    orchestrator = platform.orchestrator

    if "hint" in label:
        return orchestrator.request_hint(session)
    if "explain" in label:
        topic = task.title if task is not None else "this concept"
        return orchestrator.explain(session, topic, level=level, depth=depth)
    if "roadmap" in label:
        titles = " -> ".join(m.title for m in platform.curriculum_service.project.modules)
        return TurnResult(
            session=session, heading="PROJECT ROADMAP", status_message=titles
        )
    if any(word in label for word in ("example", "partial", "generate", "reference")):
        return TurnResult(
            session=session,
            heading=option.label,
            status_message="See the templates/ directory for a worked reference example.",
        )
    if "validate" in label:
        return orchestrator.run_tool(session, tool_name="terraform", operation="validate")
    if "plan" in label:
        return orchestrator.run_tool(session, tool_name="terraform", operation="plan")
    if "run it" in label:
        orchestrator.run_tool(session, tool_name="docker", operation="build")
        return orchestrator.run_tool(session, tool_name="docker", operation="run")

    return orchestrator.advance(session, level=level, depth=depth)
