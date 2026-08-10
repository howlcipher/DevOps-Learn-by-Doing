import pytest

from devops_learn.ai.anthropic_provider import AnthropicProvider
from devops_learn.domain.enums import AssistanceLevel, ExplanationDepth


def test_provider_is_importable_and_instantiable_without_credentials(monkeypatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    provider = AnthropicProvider()  # must not raise
    assert provider is not None


def test_calling_without_credentials_raises_a_clear_error(monkeypatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    provider = AnthropicProvider(api_key=None)
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        provider.explain_topic(
            "Docker", level=AssistanceLevel.GUIDED, depth=ExplanationDepth.NORMAL
        )
