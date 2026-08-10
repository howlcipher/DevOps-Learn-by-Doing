"""Deterministic LLMProvider used by tests and by simulation mode by default.

No network calls, no randomness: same input always produces the same output,
so curriculum/troubleshooting flows built on it are reliably testable end to
end without any real AI credentials.
"""

from __future__ import annotations

from devops_learn.ai.provider import LLMProvider
from devops_learn.ai.types import ArchitectureExplanation, TroubleshootingFeedback, TutorExplanation
from devops_learn.domain.curriculum_models import Task
from devops_learn.domain.enums import AssistanceLevel, ExplanationDepth
from devops_learn.domain.tutor_models import Assessment, Recommendation, RecommendationAlternative
from devops_learn.domain.troubleshooting_models import EvidenceSource, FailureScenario


class MockLLMProvider(LLMProvider):
    def explain_topic(
        self, topic: str, *, level: AssistanceLevel, depth: ExplanationDepth
    ) -> TutorExplanation:
        body = f"Here is what matters about {topic}, at {depth.name.lower()} depth."
        if depth in (ExplanationDepth.LEARNING, ExplanationDepth.DEEP):
            body += " This connects to the platform concepts you have already covered."
        return TutorExplanation(title=topic, body=body)

    def assess_open_response(self, task: Task, learner_response: str) -> Assessment:
        response = learner_response.strip()
        if not response:
            return Assessment(
                task_id=task.id,
                feedback="Try writing down what you expect to happen, even a guess.",
                is_correct=None,
            )
        return Assessment(
            task_id=task.id,
            feedback=(
                f"Recorded: \"{response}\". Compare this against what actually happens next."
            ),
            is_correct=None,
        )

    def recommend(self, title_hint: str, context: str) -> Recommendation:
        return Recommendation(
            title=title_hint,
            recommendation=f"Proceed with {title_hint.lower()}.",
            reason=context,
            learning_value="Medium: reinforces a concept you will reuse later.",
            alternatives=(
                RecommendationAlternative(
                    option="Skip and continue",
                    why_not_preferred="Skips a chance to practice the concept hands-on.",
                ),
            ),
        )

    def give_troubleshooting_feedback(
        self, scenario: FailureScenario, chosen_source: EvidenceSource
    ) -> TroubleshootingFeedback:
        if chosen_source.is_relevant:
            return TroubleshootingFeedback(
                is_on_track=True,
                message=f"{chosen_source.label} is a reasonable place to look here.",
            )
        return TroubleshootingFeedback(
            is_on_track=False,
            message=(
                f"{chosen_source.label} does not explain this failure. "
                "Consider what else could be involved."
            ),
        )

    def explain_architecture(self, topic: str) -> ArchitectureExplanation:
        return ArchitectureExplanation(
            title=topic,
            body=f"{topic} sits between the components you have already built and operated.",
        )

    def narrate_summary(self, summary_lines: tuple[str, ...]) -> str:
        return " ".join(summary_lines)
