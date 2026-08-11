"""Deterministic LLMProvider used by tests and by simulation mode by default.

No network calls, no randomness: same input always produces the same output.
"""

from __future__ import annotations

from devops_learn.ai.provider import LLMProvider
from devops_learn.ai.types import ArchitectureExplanation, TopicExplanation
from devops_learn.domain.enums import ExplanationDepth


class MockLLMProvider(LLMProvider):
    def explain_topic(self, topic: str, *, depth: ExplanationDepth) -> TopicExplanation:
        body = f"Here is what matters about {topic}, at {depth.name.lower()} depth."
        if depth in (ExplanationDepth.LEARNING, ExplanationDepth.DEEP):
            body += " This connects to the architecture already proposed for this project."
        return TopicExplanation(title=topic, body=body)

    def explain_architecture(self, topic: str) -> ArchitectureExplanation:
        return ArchitectureExplanation(
            title=topic,
            body=f"{topic} sits between the components already proposed for this project.",
        )

    def narrate_summary(self, summary_lines: tuple[str, ...]) -> str:
        return " ".join(summary_lines)
