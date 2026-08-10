import json
import sys
from types import ModuleType
from typing import Any

import pytest

from devops_learn.ai.anthropic_provider import DEFAULT_MODEL, AnthropicProvider
from devops_learn.domain.curriculum_models import Task
from devops_learn.domain.enums import AssistanceLevel, ExplanationDepth
from devops_learn.troubleshooting.scenarios import build_container_wont_start_scenario


class _TextBlock:
    type = "text"

    def __init__(self, text: str) -> None:
        self.text = text


class _ThinkingBlock:
    type = "thinking"
    text = "ignored"


class _Response:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.content = [_ThinkingBlock(), _TextBlock(json.dumps(payload))]


class _Messages:
    def __init__(self, payload: dict[str, Any], calls: list[dict[str, Any]]) -> None:
        self._payload = payload
        self._calls = calls

    def create(self, **kwargs: Any) -> _Response:
        self._calls.append(kwargs)
        return _Response(self._payload)


class _FakeClient:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.calls: list[dict[str, Any]] = []
        self.messages = _Messages(payload, self.calls)


def _provider_with(payload: dict[str, Any]) -> tuple[AnthropicProvider, _FakeClient]:
    provider = AnthropicProvider(api_key="test-key")
    client = _FakeClient(payload)
    provider._client = client
    return provider, client


def test_provider_is_importable_and_instantiable_without_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    provider = AnthropicProvider()  # must not raise
    assert provider is not None


def test_calling_without_credentials_raises_a_clear_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    provider = AnthropicProvider(api_key=None)
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        provider.explain_topic(
            "Docker", level=AssistanceLevel.GUIDED, depth=ExplanationDepth.NORMAL
        )


def test_the_api_key_is_read_from_the_environment_when_not_passed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "env-key")
    provider = AnthropicProvider()

    assert provider._api_key == "env-key"


def test_a_missing_anthropic_package_produces_an_install_hint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(sys.modules, "anthropic", None)
    provider = AnthropicProvider(api_key="test-key")

    with pytest.raises(RuntimeError, match="devops-learn\\[anthropic\\]"):
        provider.explain_architecture("ingress")


def test_the_client_is_built_once_from_the_anthropic_package(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    constructed: list[str | None] = []

    class _Anthropic:
        def __init__(self, api_key: str | None = None) -> None:
            constructed.append(api_key)
            self.messages = _Messages({"title": "t", "body": "b"}, [])

    fake_module = ModuleType("anthropic")
    fake_module.Anthropic = _Anthropic  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "anthropic", fake_module)

    provider = AnthropicProvider(api_key="test-key")
    provider.explain_architecture("ingress")
    provider.explain_architecture("ingress")

    assert constructed == ["test-key"]


def test_explain_topic_sends_level_and_depth_and_parses_the_reply() -> None:
    provider, client = _provider_with({"title": "Docker", "body": "Containers package apps."})

    explanation = provider.explain_topic(
        "Docker", level=AssistanceLevel.CHALLENGE, depth=ExplanationDepth.DEEP
    )

    assert explanation.title == "Docker"
    assert explanation.body == "Containers package apps."
    request = client.calls[0]
    assert request["model"] == DEFAULT_MODEL
    assert "CHALLENGE" in request["messages"][0]["content"]
    assert "DEEP" in request["messages"][0]["content"]


def test_a_custom_model_is_passed_through() -> None:
    provider = AnthropicProvider(api_key="test-key", model="claude-test")
    client = _FakeClient({"title": "t", "body": "b"})
    provider._client = client

    provider.explain_architecture("ingress")

    assert client.calls[0]["model"] == "claude-test"


def test_assess_open_response_defaults_is_correct_to_none() -> None:
    provider, client = _provider_with({"feedback": "Reasonable prediction."})
    task = Task(
        id="task_write_dockerfile",
        title="Containerize",
        goal="Write a Dockerfile",
        content=(),
        competency_codes=(),
    )

    assessment = provider.assess_open_response(task, "it will crash")

    assert assessment.task_id == "task_write_dockerfile"
    assert assessment.feedback == "Reasonable prediction."
    assert assessment.is_correct is None
    assert "it will crash" in client.calls[0]["messages"][0]["content"]


def test_recommend_maps_the_single_alternative() -> None:
    provider, _ = _provider_with(
        {
            "recommendation": "Use a multi-stage build",
            "reason": "Smaller images",
            "learning_value": "High",
            "alternative_option": "Single stage",
            "alternative_why_not": "Ships build tooling to production",
        }
    )

    recommendation = provider.recommend("Image strategy", "You have a Python API")

    assert recommendation.title == "Image strategy"
    assert recommendation.recommendation == "Use a multi-stage build"
    assert len(recommendation.alternatives) == 1
    assert recommendation.alternatives[0].option == "Single stage"
    assert recommendation.alternatives[0].why_not_preferred == (
        "Ships build tooling to production"
    )


def test_troubleshooting_feedback_includes_the_inspected_evidence() -> None:
    provider, client = _provider_with({"is_on_track": True, "message": "Good first look."})
    scenario = build_container_wont_start_scenario()
    source = scenario.steps[0].sources[1]

    feedback = provider.give_troubleshooting_feedback(scenario, source)

    assert feedback.is_on_track is True
    assert feedback.message == "Good first look."
    assert source.evidence_text in client.calls[0]["messages"][0]["content"]


def test_explain_architecture_parses_title_and_body() -> None:
    provider, _ = _provider_with({"title": "Ingress", "body": "It routes traffic."})

    explanation = provider.explain_architecture("Ingress")

    assert explanation.title == "Ingress"
    assert explanation.body == "It routes traffic."


def test_narrate_summary_joins_the_lines_into_the_prompt() -> None:
    provider, client = _provider_with({"narrative": "You containerized the API."})

    narrative = provider.narrate_summary(("Line one.", "Line two."))

    assert narrative == "You containerized the API."
    assert client.calls[0]["messages"][0]["content"] == "Line one.\nLine two."
