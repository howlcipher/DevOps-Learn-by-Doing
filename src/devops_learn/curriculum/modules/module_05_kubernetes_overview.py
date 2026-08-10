"""Module 5: Kubernetes concept overview.

Deliberately a stub: introduces the vocabulary (CONCEPT_INTRODUCED) without a
task requiring learner action. V1 proves the curriculum engine can represent
a lighter-weight later module; full Kubernetes lessons are a later milestone.
"""

from __future__ import annotations

from devops_learn.domain.content import ContentBlock
from devops_learn.domain.curriculum_models import Lesson, Module
from devops_learn.domain.enums import CompetencyCode, ContentBlockKind, ExplanationDepth


def build_module() -> Module:
    lesson = Lesson(
        id="lesson_kubernetes_overview",
        title="Kubernetes: the concepts ahead",
        content=(
            ContentBlock(
                kind=ContentBlockKind.WHY,
                text=(
                    "Once your image exists and your infrastructure is declared, something "
                    "needs to keep the right number of copies running, route traffic to "
                    "them, and replace ones that fail. That is what Kubernetes does."
                ),
                always_include=True,
            ),
            ContentBlock(
                kind=ContentBlockKind.WHAT,
                text=(
                    "A Pod runs one or more containers together. A Deployment manages a set "
                    "of identical Pods and their rollouts. A Service gives a stable network "
                    "identity to a changing set of Pods."
                ),
            ),
            ContentBlock(
                kind=ContentBlockKind.DETAIL,
                text=(
                    "Readiness and liveness probes, ConfigMaps, Secrets, namespaces, and "
                    "rolling updates build directly on these three concepts; you will meet "
                    "them once you are operating a running deployment, not before."
                ),
                min_depth=ExplanationDepth.DEEP,
            ),
        ),
    )

    return Module(
        id="module_05_kubernetes_overview",
        title="Kubernetes overview",
        why_it_matters=(
            "Knowing the vocabulary before you meet it in a failure or a manifest makes "
            "the later hands-on modules far faster to learn."
        ),
        lessons=(lesson,),
        competency_focus=(
            CompetencyCode.KUBERNETES_PODS,
            CompetencyCode.KUBERNETES_DEPLOYMENTS,
            CompetencyCode.KUBERNETES_SERVICES,
        ),
    )
