"""LLM-facing response DTOs with no persisted identity.

These are freeform-text explanations only. Anything that drives a decision
(requirements, recommendations, architecture, plan, risk) is a typed domain
dataclass produced deterministically by this platform's own services, never
invented by an LLMProvider; see docs/adr/0008-structured-ai-output.md.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TopicExplanation:
    title: str
    body: str


@dataclass(frozen=True)
class ArchitectureExplanation:
    title: str
    body: str
    diagram_hint: str | None = None
