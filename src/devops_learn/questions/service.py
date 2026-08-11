"""QuestionService: decides which clarifying questions are actually material.

Only asks what cannot be safely inferred from the ProjectAssessment plus
whatever the caller already supplied (e.g. via CLI flags). See the product
spec's "avoid trivial implementation questions" guidance.
"""

from __future__ import annotations

from devops_learn.domain.question_models import ClarifyingQuestion


class QuestionService:
    def material_questions(
        self,
        *,
        environment_known: bool,
        public_access_known: bool,
        cost_priority_known: bool,
        wants_kubernetes_experience: bool,
    ) -> tuple[ClarifyingQuestion, ...]:
        questions: list[ClarifyingQuestion] = []
        if not environment_known:
            questions.append(
                ClarifyingQuestion(
                    id="environment",
                    category="environment",
                    prompt="Is this development-only or production-like?",
                    options=("Development", "Production-like", "Production"),
                )
            )
        if not public_access_known:
            questions.append(
                ClarifyingQuestion(
                    id="public_access",
                    category="availability",
                    prompt="Should the API be publicly accessible?",
                    options=("Yes, public", "No, private only"),
                )
            )
        if not cost_priority_known:
            questions.append(
                ClarifyingQuestion(
                    id="cost_priority",
                    category="cost",
                    prompt="Should we optimize primarily for cost or availability?",
                    options=("Lowest cost", "Balanced", "Highest availability"),
                )
            )
        if wants_kubernetes_experience:
            questions.append(
                ClarifyingQuestion(
                    id="kubernetes_reason",
                    category="learning_objectives",
                    prompt=(
                        "Do you want Kubernetes because the workload requires it, because you "
                        "want to learn it, or both?"
                    ),
                    options=("Workload requires it", "Learning objective", "Both"),
                )
            )
        return tuple(questions)
