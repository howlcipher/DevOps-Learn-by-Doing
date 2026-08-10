import argparse
from typing import Any

import pytest

from devops_learn.cli.commands import resume
from devops_learn.domain.enums import AssistanceLevel, ExplanationDepth
from devops_learn.domain.learner_models import LearningSession
from devops_learn.tutor.bootstrap import Platform


@pytest.fixture()
def resumed(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []

    def fake_resume(
        platform: Platform,
        session: LearningSession,
        *,
        level: AssistanceLevel,
        depth: ExplanationDepth,
    ) -> None:
        calls.append({"session": session, "level": level, "depth": depth})

    monkeypatch.setattr(resume, "resume_interactive_session", fake_resume)
    return calls


def test_prompts_to_start_when_no_profile_exists(
    platform: Platform, resumed: list[dict[str, Any]], capsys: pytest.CaptureFixture[str]
) -> None:
    resume.run(argparse.Namespace(), platform)

    assert "devops-learn start" in capsys.readouterr().out
    assert resumed == []


def test_reports_when_a_profile_has_no_active_session(
    platform: Platform,
    learner_id: int,
    resumed: list[dict[str, Any]],
    capsys: pytest.CaptureFixture[str],
) -> None:
    resume.run(argparse.Namespace(), platform)

    assert "No active session to resume" in capsys.readouterr().out
    assert resumed == []


def test_resumes_the_latest_session_with_the_profile_preferences(
    platform: Platform, learner_id: int, resumed: list[dict[str, Any]]
) -> None:
    session = platform.session_service.start_new_session(
        learner_id, platform.curriculum_service.project.id, simulation_mode=True
    )

    resume.run(argparse.Namespace(), platform)

    assert len(resumed) == 1
    assert resumed[0]["session"].id == session.id
    assert resumed[0]["level"] is AssistanceLevel.CHALLENGE
    assert resumed[0]["depth"] is ExplanationDepth.DEEP
