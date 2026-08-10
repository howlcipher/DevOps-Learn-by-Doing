"""LLMProvider: the only seam between business logic and any specific AI SDK.

Every method returns a typed domain or ai.types structured value, never a raw
string the caller has to parse. Business logic (curriculum, competencies,
troubleshooting, recommendations) depends only on this ABC, so it can run
identically against MockLLMProvider in tests/simulation and against a real
provider without any conditional logic elsewhere.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from devops_learn.ai.types import ArchitectureExplanation, TroubleshootingFeedback, TutorExplanation
from devops_learn.domain.curriculum_models import Task
from devops_learn.domain.enums import AssistanceLevel, ExplanationDepth
from devops_learn.domain.tutor_models import Assessment, Recommendation
from devops_learn.domain.troubleshooting_models import EvidenceSource, FailureScenario


class LLMProvider(ABC):
    @abstractmethod
    def explain_topic(
        self, topic: str, *, level: AssistanceLevel, depth: ExplanationDepth
    ) -> TutorExplanation:
        """Freeform explanation for the 'explain' command and the Explain control."""

    @abstractmethod
    def assess_open_response(self, task: Task, learner_response: str) -> Assessment:
        """Evaluates a free-text answer (prediction, explain-in-your-own-words)."""

    @abstractmethod
    def recommend(self, title_hint: str, context: str) -> Recommendation:
        """Produces a structured recommendation for a decision point."""

    @abstractmethod
    def give_troubleshooting_feedback(
        self, scenario: FailureScenario, chosen_source: EvidenceSource
    ) -> TroubleshootingFeedback:
        """Reacts to one evidence source the learner chose to inspect."""

    @abstractmethod
    def explain_architecture(self, topic: str) -> ArchitectureExplanation:
        """Used by the architecture review step and deep-dive requests."""

    @abstractmethod
    def narrate_summary(self, summary_lines: tuple[str, ...]) -> str:
        """Turns deterministic summary lines into a short, friendly paragraph."""
