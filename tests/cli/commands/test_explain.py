import argparse

import pytest

from devops_learn.ai.types import TutorExplanation
from devops_learn.cli.commands import explain
from devops_learn.domain.enums import AssistanceLevel, ExplanationDepth
from devops_learn.tutor.bootstrap import Platform


class _RecordingProvider:
    """Captures the level/depth the command resolved before calling the LLM."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, AssistanceLevel, ExplanationDepth]] = []

    def explain_topic(
        self, topic: str, *, level: AssistanceLevel, depth: ExplanationDepth
    ) -> TutorExplanation:
        self.calls.append((topic, level, depth))
        return TutorExplanation(title="readiness probes", body="A probe reports health.")


def test_joins_topic_words_and_prints_title_and_body(
    platform: Platform, capsys: pytest.CaptureFixture[str]
) -> None:
    provider = _RecordingProvider()
    platform.llm = provider  # type: ignore[assignment]

    explain.run(argparse.Namespace(topic=["readiness", "probes"]), platform)
    output = capsys.readouterr().out

    assert provider.calls[0][0] == "readiness probes"
    assert "READINESS PROBES" in output
    assert "A probe reports health." in output


def test_falls_back_to_guided_normal_without_a_profile(platform: Platform) -> None:
    provider = _RecordingProvider()
    platform.llm = provider  # type: ignore[assignment]

    explain.run(argparse.Namespace(topic=["docker"]), platform)

    assert provider.calls[0][1:] == (AssistanceLevel.GUIDED, ExplanationDepth.NORMAL)


def test_uses_the_stored_profile_preferences_when_one_exists(
    platform: Platform, learner_id: int
) -> None:
    provider = _RecordingProvider()
    platform.llm = provider  # type: ignore[assignment]

    explain.run(argparse.Namespace(topic=["docker"]), platform)

    assert provider.calls[0][1:] == (AssistanceLevel.CHALLENGE, ExplanationDepth.DEEP)
