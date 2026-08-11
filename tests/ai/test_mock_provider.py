from devops_learn.ai.mock_provider import MockLLMProvider
from devops_learn.domain.enums import ExplanationDepth


def test_explain_topic_is_deterministic() -> None:
    provider = MockLLMProvider()
    first = provider.explain_topic("Dockerfiles", depth=ExplanationDepth.NORMAL)
    second = provider.explain_topic("Dockerfiles", depth=ExplanationDepth.NORMAL)
    assert first == second
    assert first.title == "Dockerfiles"


def test_explain_architecture_returns_a_title_and_body() -> None:
    provider = MockLLMProvider()
    explanation = provider.explain_architecture("Virtual Network")
    assert explanation.title == "Virtual Network"
    assert explanation.body


def test_narrate_summary_does_not_invent_facts() -> None:
    provider = MockLLMProvider()
    lines = ("Docker: built.", "Terraform: applied.")
    narrative = provider.narrate_summary(lines)
    assert "Docker: built." in narrative
    assert "Terraform: applied." in narrative
