"""Real LLMProvider adapter, backed by the Anthropic API.

Importable and instantiable with zero credentials present; it only raises
once a method is actually called without an API key, so simulation mode and
the test suite never need this to succeed. The 'anthropic' package itself is
an optional dependency (pip install 'devops-learn[anthropic]'), imported lazily
so the rest of the platform has no hard dependency on one AI SDK.
"""

from __future__ import annotations

import json
import os
from typing import Any

from devops_learn.ai.provider import LLMProvider
from devops_learn.ai.types import ArchitectureExplanation, TroubleshootingFeedback, TutorExplanation
from devops_learn.domain.curriculum_models import Task
from devops_learn.domain.enums import AssistanceLevel, ExplanationDepth
from devops_learn.domain.tutor_models import Assessment, Recommendation, RecommendationAlternative
from devops_learn.domain.troubleshooting_models import EvidenceSource, FailureScenario

DEFAULT_MODEL = "claude-sonnet-5"


class AnthropicProvider(LLMProvider):
    def __init__(self, api_key: str | None = None, model: str = DEFAULT_MODEL) -> None:
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self._model = model
        self._client: Any | None = None

    def _client_or_raise(self) -> Any:
        if self._client is not None:
            return self._client
        if not self._api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. AnthropicProvider needs credentials only "
                "when actually called; simulation mode uses MockLLMProvider instead."
            )
        try:
            import anthropic
        except ImportError as exc:
            raise RuntimeError(
                "The 'anthropic' package is not installed. Install it with "
                "pip install 'devops-learn[anthropic]', or use MockLLMProvider "
                "(the default in simulation mode)."
            ) from exc
        self._client = anthropic.Anthropic(api_key=self._api_key)
        return self._client

    def _complete_json(self, system: str, user: str) -> dict[str, Any]:
        client = self._client_or_raise()
        response = client.messages.create(
            model=self._model,
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        text = "".join(block.text for block in response.content if block.type == "text")
        result: dict[str, Any] = json.loads(text)
        return result

    def explain_topic(
        self, topic: str, *, level: AssistanceLevel, depth: ExplanationDepth
    ) -> TutorExplanation:
        data = self._complete_json(
            system=(
                "You are a DevOps tutor. Reply with JSON: "
                '{"title": str, "body": str}. Be precise, no filler.'
            ),
            user=(
                f"Explain '{topic}' to a learner at assistance level {level.name} and "
                f"explanation depth {depth.name}."
            ),
        )
        return TutorExplanation(title=data["title"], body=data["body"])

    def assess_open_response(self, task: Task, learner_response: str) -> Assessment:
        data = self._complete_json(
            system=(
                "You assess a learner's free-text DevOps answer. Reply with JSON: "
                '{"feedback": str, "is_correct": bool or null}. Use null when there is no '
                "single right answer (predictions, explain-in-your-own-words)."
            ),
            user=f"Task: {task.title}\nGoal: {task.goal}\nLearner answer: {learner_response}",
        )
        return Assessment(
            task_id=task.id, feedback=data["feedback"], is_correct=data.get("is_correct")
        )

    def recommend(self, title_hint: str, context: str) -> Recommendation:
        data = self._complete_json(
            system=(
                "You produce a structured DevOps recommendation. Reply with JSON: "
                '{"recommendation": str, "reason": str, "learning_value": str, '
                '"alternative_option": str, "alternative_why_not": str}.'
            ),
            user=f"Decision point: {title_hint}\nContext: {context}",
        )
        return Recommendation(
            title=title_hint,
            recommendation=data["recommendation"],
            reason=data["reason"],
            learning_value=data["learning_value"],
            alternatives=(
                RecommendationAlternative(
                    option=data["alternative_option"],
                    why_not_preferred=data["alternative_why_not"],
                ),
            ),
        )

    def give_troubleshooting_feedback(
        self, scenario: FailureScenario, chosen_source: EvidenceSource
    ) -> TroubleshootingFeedback:
        data = self._complete_json(
            system=(
                "You give short feedback on a troubleshooting step. Reply with JSON: "
                '{"is_on_track": bool, "message": str}.'
            ),
            user=(
                f"Scenario: {scenario.narrative}\n"
                f"Learner inspected: {chosen_source.label}\n"
                f"What it revealed: {chosen_source.evidence_text}"
            ),
        )
        return TroubleshootingFeedback(
            is_on_track=data["is_on_track"], message=data["message"]
        )

    def explain_architecture(self, topic: str) -> ArchitectureExplanation:
        data = self._complete_json(
            system=(
                "You explain one piece of system architecture. Reply with JSON: "
                '{"title": str, "body": str}.'
            ),
            user=f"Explain the architecture concept: {topic}",
        )
        return ArchitectureExplanation(title=data["title"], body=data["body"])

    def narrate_summary(self, summary_lines: tuple[str, ...]) -> str:
        data = self._complete_json(
            system=(
                "You rewrite a bullet list of learning progress facts as one short, "
                'friendly paragraph. Do not invent facts. Reply with JSON: {"narrative": str}.'
            ),
            user="\n".join(summary_lines),
        )
        narrative: str = data["narrative"]
        return narrative
