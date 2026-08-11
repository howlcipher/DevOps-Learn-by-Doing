"""LLMProvider: the only seam between business logic and any specific AI SDK.

Every method returns a typed ai.types DTO, never a raw string the caller has
to parse. Business logic (recommendations, architecture, explanations) does
not depend on this ABC at all for decisions: it only narrates or explains
already-decided, deterministic structures. See docs/adr/0008.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from devops_learn.ai.types import ArchitectureExplanation, TopicExplanation
from devops_learn.domain.enums import ExplanationDepth


class LLMProvider(ABC):
    @abstractmethod
    def explain_topic(self, topic: str, *, depth: ExplanationDepth) -> TopicExplanation:
        """Freeform explanation for the 'explain' command and Explain/Why controls."""

    @abstractmethod
    def explain_architecture(self, topic: str) -> ArchitectureExplanation:
        """Used by architecture review and deep-dive requests."""

    @abstractmethod
    def narrate_summary(self, summary_lines: tuple[str, ...]) -> str:
        """Turns deterministic summary lines into a short, friendly paragraph.
        Must never invent facts not present in summary_lines."""
