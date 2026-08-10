"""Covers the REPL's input dispatch: keywords, menu labels, and troubleshooting keys."""

import pytest

from devops_learn.cli import session_loop
from devops_learn.curriculum.modules.module_03_troubleshoot_failure import (
    TROUBLESHOOT_CONTAINER_WONT_START_TASK_ID,
)
from devops_learn.curriculum.modules.module_04_terraform_plan import TERRAFORM_PLAN_TASK_ID
from devops_learn.domain.content import MenuOption
from devops_learn.domain.enums import AssistanceLevel, ExplanationDepth
from devops_learn.tutor.bootstrap import Platform
from devops_learn.tutor.orchestrator import TurnResult

LEVEL = AssistanceLevel.GUIDED
DEPTH = ExplanationDepth.LEARNING


def _script(monkeypatch: pytest.MonkeyPatch, answers: list[str]) -> None:
    remaining = iter(answers)
    monkeypatch.setattr("builtins.input", lambda *_: next(remaining))


def _begin(platform: Platform, learner_id: int) -> TurnResult:
    return platform.orchestrator.begin_project(
        learner_id=learner_id,
        project_id=platform.curriculum_service.project.id,
        simulation_mode=True,
        level=LEVEL,
        depth=DEPTH,
    )


def _dispatch(platform: Platform, turn: TurnResult, raw: str) -> TurnResult:
    return session_loop._dispatch(platform, turn, raw, level=LEVEL, depth=DEPTH)


def _select(
    platform: Platform, turn: TurnResult, label: str, *, with_task: bool = True
) -> TurnResult:
    task = (
        platform.curriculum_service.task(turn.session.current_task_id)
        if with_task and turn.session.current_task_id
        else None
    )
    return session_loop._handle_menu_selection(
        platform, turn.session, task, MenuOption("Z", label), level=LEVEL, depth=DEPTH
    )


def _advance_to_task(platform: Platform, turn: TurnResult, task_id: str) -> TurnResult:
    for _ in range(50):
        if turn.session.current_task_id == task_id:
            return turn
        turn = platform.orchestrator.advance(turn.session, level=LEVEL, depth=DEPTH)
    raise AssertionError(f"never reached task '{task_id}'")


def test_run_interactive_session_renders_the_first_turn_and_stops_on_quit(
    platform: Platform,
    learner_id: int,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _script(monkeypatch, ["hint", "quit"])

    session_loop.run_interactive_session(platform, learner_id, level=LEVEL, depth=DEPTH)
    output = capsys.readouterr().out

    assert "UNDERSTAND THE WORKLOAD" in output
    assert "HINT 1" in output
    assert "devops-learn resume" in output


def test_resume_interactive_session_stops_on_eof(
    platform: Platform,
    learner_id: int,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    session = _begin(platform, learner_id).session

    def raise_eof(*_: object) -> str:
        raise EOFError

    monkeypatch.setattr("builtins.input", raise_eof)
    session_loop.resume_interactive_session(platform, session, level=LEVEL, depth=DEPTH)

    assert "UNDERSTAND THE WORKLOAD" in capsys.readouterr().out


def test_advance_synonyms_move_to_the_next_task(platform: Platform, learner_id: int) -> None:
    turn = _begin(platform, learner_id)
    first_task_id = turn.session.current_task_id

    for synonym in ("advance", "continue", "next"):
        turn = _dispatch(platform, turn, synonym)
        assert turn.session.current_task_id != first_task_id


def test_explain_without_a_topic_falls_back_to_the_heading(
    platform: Platform, learner_id: int
) -> None:
    turn = _begin(platform, learner_id)

    explained = _dispatch(platform, turn, "explain")

    assert explained.heading == turn.heading


def test_explain_with_a_topic_uses_that_topic(platform: Platform, learner_id: int) -> None:
    turn = _begin(platform, learner_id)

    explained = _dispatch(platform, turn, "explain readiness probes")

    assert explained.heading == "readiness probes"


def test_a_check_question_key_is_graded(platform: Platform, learner_id: int) -> None:
    turn = _begin(platform, learner_id)

    graded = _dispatch(platform, turn, "B")

    assert graded.status_message is not None
    assert "Correct" in graded.status_message


def test_unrecognized_input_returns_guidance_without_changing_the_turn(
    platform: Platform, learner_id: int
) -> None:
    turn = _begin(platform, learner_id)

    result = _dispatch(platform, turn, "what now?")

    assert result.status_message is not None
    assert "I didn't understand that" in result.status_message
    assert result.menu == turn.menu


def test_free_text_on_a_prediction_task_is_assessed(platform: Platform, learner_id: int) -> None:
    turn = _dispatch(platform, _begin(platform, learner_id), "advance")
    assert turn.prediction is not None

    result = _dispatch(platform, turn, "the container exits immediately")

    assert result.status_message is not None
    assert "the container exits immediately" in result.status_message


def test_menu_selection_is_matched_by_label_on_the_current_turn(
    platform: Platform, learner_id: int
) -> None:
    turn = _dispatch(platform, _begin(platform, learner_id), "advance")
    hint_key = next(option.key for option in turn.menu if "hint" in option.label.lower())

    hinted = _dispatch(platform, turn, hint_key)

    assert hinted.status_message is not None
    assert "HINT 1" in hinted.status_message


@pytest.mark.parametrize(
    ("label", "expected_heading"),
    [
        ("Show me the entire project roadmap", "PROJECT ROADMAP"),
        ("Run terraform validate", "terraform validate"),
        ("Run terraform plan", "terraform plan"),
        ("Run it", "docker run"),
    ],
)
def test_menu_labels_route_to_the_matching_action(
    platform: Platform, learner_id: int, label: str, expected_heading: str
) -> None:
    turn = _begin(platform, learner_id)

    result = _select(platform, turn, label)

    assert result.heading == expected_heading


@pytest.mark.parametrize(
    "label", ["Show me a partial example", "Show me the reference configuration"]
)
def test_menu_labels_offering_worked_code_point_at_templates(
    platform: Platform, learner_id: int, label: str
) -> None:
    turn = _begin(platform, learner_id)

    result = _select(platform, turn, label)

    assert result.status_message is not None
    assert "templates/" in result.status_message


def test_a_menu_label_matching_explain_explains_the_task(
    platform: Platform, learner_id: int
) -> None:
    turn = _begin(platform, learner_id)
    assert turn.session.current_task_id is not None
    task = platform.curriculum_service.task(turn.session.current_task_id)

    assert _select(platform, turn, "Explain the code").heading == task.title
    assert (
        _select(platform, turn, "Explain the code", with_task=False).heading == "this concept"
    )


def test_an_unmatched_menu_label_falls_back_to_advancing(
    platform: Platform, learner_id: int
) -> None:
    turn = _begin(platform, learner_id)

    result = _select(platform, turn, "Inspect the Python application")

    assert result.session.current_task_id != turn.session.current_task_id


def test_terraform_menu_keys_are_dispatched_from_raw_input(
    platform: Platform, learner_id: int
) -> None:
    turn = _advance_to_task(platform, _begin(platform, learner_id), TERRAFORM_PLAN_TASK_ID)
    validate_key = next(o.key for o in turn.menu if "validate" in o.label.lower())

    assert _dispatch(platform, turn, validate_key).heading == "terraform validate"


def test_troubleshooting_evidence_letter_reveals_that_source(
    platform: Platform, learner_id: int
) -> None:
    turn = _advance_to_task(
        platform, _begin(platform, learner_id), TROUBLESHOOT_CONTAINER_WONT_START_TASK_ID
    )

    result = _dispatch(platform, turn, "B")

    assert result.status_message is not None
    assert "Container logs" in result.status_message


def test_troubleshooting_letter_that_matches_no_evidence_source_falls_through(
    platform: Platform, learner_id: int
) -> None:
    turn = _advance_to_task(
        platform, _begin(platform, learner_id), TROUBLESHOOT_CONTAINER_WONT_START_TASK_ID
    )

    result = _dispatch(platform, turn, "Z")

    assert result.status_message is not None
    assert "Container logs" not in result.status_message


def test_troubleshooting_diagnosis_is_submitted_and_bad_keys_are_rejected(
    platform: Platform, learner_id: int
) -> None:
    turn = _advance_to_task(
        platform, _begin(platform, learner_id), TROUBLESHOOT_CONTAINER_WONT_START_TASK_ID
    )

    rejected = _dispatch(platform, turn, "diagnose Z")
    assert rejected.status_message is not None
    assert "Unrecognized diagnosis letter" in rejected.status_message

    correct = _dispatch(platform, turn, "diagnose A")
    assert correct.status_message is not None
    assert "Correct." in correct.status_message
