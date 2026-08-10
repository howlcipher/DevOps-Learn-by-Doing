import argparse
from typing import Any

import pytest

from devops_learn.cli.commands import start
from devops_learn.domain.enums import (
    AssistanceLevel,
    CloudProviderKind,
    ExplanationDepth,
    LanguageTrackKind,
)
from devops_learn.tutor.bootstrap import Platform


@pytest.fixture()
def started(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []

    def fake_run_session(
        platform: Platform,
        learner_id: int,
        *,
        level: AssistanceLevel,
        depth: ExplanationDepth,
        simulation_mode: bool = True,
    ) -> None:
        calls.append(
            {
                "learner_id": learner_id,
                "level": level,
                "depth": depth,
                "simulation_mode": simulation_mode,
            }
        )

    monkeypatch.setattr(start, "run_interactive_session", fake_run_session)
    return calls


def _script(monkeypatch: pytest.MonkeyPatch, answers: list[str]) -> None:
    remaining = iter(answers)
    monkeypatch.setattr("builtins.input", lambda *_: next(remaining))


def test_onboarding_persists_the_profile_and_starts_a_simulated_session(
    platform: Platform,
    started: list[dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _script(monkeypatch, ["1", "1", "3", "4"])

    start.run(argparse.Namespace(simulation=True), platform)
    output = capsys.readouterr().out

    profile = platform.profile_repository.latest()
    assert profile is not None
    assert profile.cloud_provider is CloudProviderKind.AZURE
    assert profile.language_track is LanguageTrackKind.PYTHON
    assert profile.assistance_level is AssistanceLevel.CHALLENGE
    assert profile.explanation_depth is ExplanationDepth.DEEP

    assert started == [
        {
            "learner_id": profile.id,
            "level": AssistanceLevel.CHALLENGE,
            "depth": ExplanationDepth.DEEP,
            "simulation_mode": True,
        }
    ]
    assert "DEVOPS LEARN" in output
    assert platform.curriculum_service.project.title in output


def test_unavailable_tracks_and_out_of_range_choices_are_rejected_and_reprompted(
    platform: Platform,
    started: list[dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _script(monkeypatch, ["2", "1", "2", "1", "9", "2", "0", "1"])

    start.run(argparse.Namespace(simulation=True), platform)
    output = capsys.readouterr().out

    assert "AWS and GCP are not implemented yet" in output
    assert "Go is not implemented yet" in output
    assert output.count("Please choose 1-4.") == 2
    assert started[0]["level"] is AssistanceLevel.ASSISTED
    assert started[0]["depth"] is ExplanationDepth.BRIEF
