"""One scripted playthrough covering every V1 mechanic end to end:

1. one Python lesson (a comprehension question)
2. one Docker lesson
3. one prediction question
4. one progressive-hint interaction
5. one simulated failure / troubleshooting exercise, reaching a diagnosis
6. one simulated Terraform plan
7. competency progression
8. session persistence and resume, and a progress/competencies summary
   built from what actually happened, not placeholder text.

This is the single source of truth for "the learning engine works end to
end"; see docs/development.md for how to run it and CONTRIBUTING.md's check
list for where it fits in the verification workflow.
"""

import sqlite3
from datetime import datetime, timezone

from devops_learn.domain.enums import (
    AssistanceLevel,
    CloudProviderKind,
    CompetencyState,
    ExplanationDepth,
    LanguageTrackKind,
)
from devops_learn.domain.learner_models import LearnerProfile
from devops_learn.tutor.bootstrap import build_platform

NOW = datetime(2026, 8, 9, 12, 0, 0, tzinfo=timezone.utc)


def test_full_playthrough(conn: sqlite3.Connection) -> None:
    platform = build_platform(conn)
    orchestrator = platform.orchestrator
    level = AssistanceLevel.GUIDED
    depth = ExplanationDepth.LEARNING

    profile = platform.profile_repository.create(
        LearnerProfile(
            display_name="Learner",
            cloud_provider=CloudProviderKind.AZURE,
            language_track=LanguageTrackKind.PYTHON,
            assistance_level=level,
            explanation_depth=depth,
            created_at=NOW,
            updated_at=NOW,
        )
    )
    assert profile.id is not None
    learner_id = profile.id

    # 1. Python lesson: module 1's comprehension question, answered correctly.
    turn = orchestrator.begin_project(
        learner_id=learner_id,
        project_id=platform.curriculum_service.project.id,
        simulation_mode=True,
        level=level,
        depth=depth,
    )
    assert "Understand the workload" in turn.heading
    turn = orchestrator.answer_question(turn.session, chosen_key="B")
    assert turn.status_message is not None and "Correct" in turn.status_message

    # --- mid-session resume check ---
    mid_session = platform.session_service.resume_latest(learner_id)
    assert mid_session is not None
    assert mid_session.current_module_id == "module_01_understand_workload"

    # 2 & 3. Docker lesson with a prediction.
    turn = orchestrator.advance(turn.session, level=level, depth=depth)
    assert "Containerize" in turn.heading
    assert turn.prediction is not None

    # 4. One progressive-hint interaction.
    hint_turn = orchestrator.request_hint(turn.session)
    assert hint_turn.status_message is not None and "HINT 1" in hint_turn.status_message
    second_hint_turn = orchestrator.request_hint(turn.session)
    assert second_hint_turn.status_message is not None
    assert "HINT 2" in second_hint_turn.status_message

    # Answer the prediction before advancing.
    prediction_turn = orchestrator.attempt_task(
        turn.session, learner_response="It will invalidate Docker's build cache."
    )
    assert prediction_turn.status_message is not None
    assert "What actually happens" in prediction_turn.status_message

    turn = orchestrator.advance(turn.session, level=level, depth=depth)

    # 5. Troubleshooting: inspect evidence, then reach the correct diagnosis.
    assert "Troubleshoot" in turn.heading
    turn = orchestrator.submit_diagnosis(turn.session, diagnosis_key="corrupted_image")
    assert turn.status_message is not None and "doesn't match" in turn.status_message
    turn = orchestrator.submit_diagnosis(turn.session, diagnosis_key="missing_port_env_var")
    assert turn.status_message is not None and "Correct" in turn.status_message

    turn = orchestrator.advance(turn.session, level=level, depth=depth)

    # 6. Terraform plan.
    assert "Terraform" in turn.heading or "Infrastructure" in turn.heading
    plan_turn = orchestrator.run_tool(
        turn.session, tool_name="terraform", operation="plan"
    )
    assert plan_turn.status_message is not None
    assert "3 to add" in plan_turn.status_message

    turn = orchestrator.advance(turn.session, level=level, depth=depth)
    assert "Kubernetes" in turn.heading

    final_turn = orchestrator.advance(turn.session, level=level, depth=depth)
    assert final_turn.is_terminal is True

    # 7. Competency progression: real states, not placeholders.
    states = {s.code.value: s.state for s in platform.competency_repository.list_states(learner_id)}
    assert states["docker"] == CompetencyState.DEMONSTRATED
    assert states["troubleshooting"] == CompetencyState.DEMONSTRATED
    assert states["python_basics"] == CompetencyState.INTRODUCED
    assert states["http_api"] == CompetencyState.INTRODUCED

    # 8. A progress summary built from what actually happened.
    summary = platform.summary_service.build_summary(learner_id)
    assert any("docker" in line.lower() for line in summary.competency_lines)
    assert any("diagnosed one failure" in line for line in summary.narrative_lines)

    # A completed project session is no longer resumable.
    assert platform.session_service.resume_latest(learner_id) is None
