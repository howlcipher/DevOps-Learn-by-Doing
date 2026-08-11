"""ExplanationService: renders Explanation/LearningMoment structures as text,
scaled by ExecutionMode and ExplanationDepth.

Kept separate from any one CLI presenter so a future web UI can reuse the
same explanation objects and only change how they are laid out.
"""

from __future__ import annotations

from devops_learn.domain.enums import ExecutionMode, ExplanationDepth
from devops_learn.domain.explanation_models import Explanation, LearningMoment


class ExplanationService:
    def render(
        self, explanation: Explanation, *, mode: ExecutionMode, depth: ExplanationDepth
    ) -> str:
        if (
            mode in (ExecutionMode.AI_EXECUTED, ExecutionMode.AUTONOMOUS)
            and depth < ExplanationDepth.DEEP
        ):
            return explanation.action
        lines = [f"ACTION\n{explanation.action}"]
        if explanation.why:
            lines.append(f"WHY\n{explanation.why}")
        if explanation.decision:
            lines.append(f"DECISION\n{explanation.decision}")
        if explanation.alternatives and depth >= ExplanationDepth.NORMAL:
            lines.append(f"ALTERNATIVE\n{explanation.alternatives}")
        if explanation.tradeoff and depth >= ExplanationDepth.NORMAL:
            lines.append(f"TRADEOFF\n{explanation.tradeoff}")
        if explanation.what_to_understand and depth >= ExplanationDepth.LEARNING:
            lines.append(f"WHAT YOU SHOULD UNDERSTAND\n{explanation.what_to_understand}")
        if explanation.result:
            lines.append(f"RESULT\n{explanation.result}")
        return "\n\n".join(lines)

    def render_learning_moment(
        self, moment: LearningMoment, *, mode: ExecutionMode, depth: ExplanationDepth
    ) -> str | None:
        if (
            mode in (ExecutionMode.AI_EXECUTED, ExecutionMode.AUTONOMOUS)
            and depth < ExplanationDepth.DEEP
        ):
            return None
        lines = [f"LEARNING MOMENT: {moment.concept}", moment.summary]
        if depth >= ExplanationDepth.LEARNING:
            lines.append(moment.why_it_matters)
        if depth >= ExplanationDepth.DEEP:
            lines.append(moment.deep_explanation)
        return "\n".join(lines)
