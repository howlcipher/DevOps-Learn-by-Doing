"""RecommendationService: turns detected requirements into structured, explained
recommendations.

Deterministic and table-driven for the decision itself (see
docs/adr/0008-structured-ai-output.md); the LLMProvider is only used to
narrate free text when one is supplied, never to decide the recommended
option. engineering_need and learning_value are always tracked separately.
"""

from __future__ import annotations

from devops_learn.domain.analysis_models import ProjectAssessment
from devops_learn.domain.enums import CostPriority, KubernetesNeed, RecommendationCategory
from devops_learn.domain.recommendation_models import Recommendation, RecommendationAlternative
from devops_learn.domain.requirements_models import DetectedRequirement


class RecommendationService:
    def build_recommendations(
        self,
        assessment: ProjectAssessment,
        requirements: tuple[DetectedRequirement, ...],
        *,
        cost_priority: CostPriority,
        wants_kubernetes_experience: bool,
    ) -> tuple[Recommendation, ...]:
        requirement_ids = {r.id for r in requirements}
        recs: list[Recommendation] = []

        if "containerization" in requirement_ids:
            recs.append(
                Recommendation(
                    id="rec_docker",
                    category=RecommendationCategory.DEPLOYMENT,
                    title="Containerize with a multi-stage Dockerfile",
                    recommendation="Add a multi-stage Dockerfile with a non-root runtime user.",
                    reason="Build tooling is needed to create the application but should not "
                    "remain in the runtime image.",
                    alternatives=(
                        RecommendationAlternative(
                            option="Single-stage Dockerfile",
                            why_not_preferred="Simpler, but ships build tooling in the runtime "
                            "image and increases attack surface.",
                        ),
                    ),
                    engineering_need="Required to produce a repeatable runtime artifact.",
                    learning_value=(
                        "Foundational: every later step (CI, Kubernetes) builds on this image."
                    ),
                    security_impact="Smaller runtime image, reduced attack surface.",
                    complexity_impact="Low: one file, one build step.",
                )
            )

        if "ci_cd" in requirement_ids:
            recs.append(
                Recommendation(
                    id="rec_ci_cd",
                    category=RecommendationCategory.CI_CD,
                    title="Add a GitHub Actions pipeline",
                    recommendation="Test -> lint -> container build -> Terraform validate/plan -> "
                    "approval -> deploy -> health verification.",
                    reason="No CI/CD exists yet; deployments are currently manual and unverified.",
                    alternatives=(
                        RecommendationAlternative(
                            option="Deploy manually from a developer's machine",
                            why_not_preferred="Not repeatable, not auditable, and error-prone.",
                        ),
                    ),
                    engineering_need="Required for repeatable, reviewable deployments.",
                    learning_value="Demonstrates a real gated deployment pipeline.",
                    reliability_impact="Adds automated test and validation gates before deploy.",
                )
            )

        if "iac" in requirement_ids:
            recs.append(
                Recommendation(
                    id="rec_terraform",
                    category=RecommendationCategory.TERRAFORM,
                    title="Use Terraform for infrastructure",
                    recommendation="Provision cloud resources with Terraform rather than by hand.",
                    reason=(
                        "Infrastructure created by hand cannot be reliably reviewed, reproduced, "
                        "or torn down."
                    ),
                    alternatives=(
                        RecommendationAlternative(
                            option="Create resources manually in the cloud console",
                            why_not_preferred=(
                                "Fast to start, but undocumented and hard to reproduce or "
                                "safely remove later."
                            ),
                        ),
                    ),
                    engineering_need="Required for repeatable, reviewable infrastructure.",
                    learning_value="Terraform state, plan, and apply are core IaC concepts.",
                    complexity_impact="Adds a state file and plan/apply workflow to learn.",
                )
            )

        if "secret_management" in requirement_ids:
            recs.append(
                Recommendation(
                    id="rec_secrets",
                    category=RecommendationCategory.SECRETS,
                    title="Use managed secrets with workload identity",
                    recommendation=(
                        "Store secrets in a managed secret store; grant access via workload "
                        "identity rather than a stored cloud credential."
                    ),
                    reason=(
                        f"{len(assessment.secret_indicators)} likely secret(s) are currently "
                        "read from the environment with no managed store behind them."
                    ),
                    alternatives=(
                        RecommendationAlternative(
                            option="Kubernetes Secret",
                            why_not_preferred="Simpler, but base64-encoded, not encrypted access-"
                            "controlled storage, and harder to rotate centrally.",
                        ),
                        RecommendationAlternative(
                            option="CI-injected secret at deploy time",
                            why_not_preferred="Keeps the secret out of the repo, but does not "
                            "centralize rotation or access review.",
                        ),
                    ),
                    engineering_need="Required: credentials should never be long-lived plaintext.",
                    learning_value="Demonstrates authentication vs. authorization for workloads.",
                    security_impact=(
                        "Removes long-lived stored credentials from the deployment path."
                    ),
                    requires_user_decision=True,
                )
            )

        if assessment.security_findings:
            recs.append(
                Recommendation(
                    id="rec_remove_hardcoded_secret",
                    category=RecommendationCategory.SECURITY,
                    title="Move hardcoded credentials out of source",
                    recommendation="Replace the hardcoded credential-shaped value with an "
                    "environment variable read at startup, then rotate it.",
                    reason=assessment.security_findings[0],
                    engineering_need=(
                        "Required: a committed credential is treated as already leaked."
                    ),
                    learning_value="Illustrates why secret scanning exists in CI.",
                    security_impact="High: removes a leaked-credential risk.",
                    requires_user_decision=True,
                )
            )

        k8s_rec = self._kubernetes_recommendation(
            assessment,
            cost_priority=cost_priority,
            wants_kubernetes_experience=wants_kubernetes_experience,
        )
        if k8s_rec is not None:
            recs.append(k8s_rec)

        if "observability" in requirement_ids:
            recs.append(
                Recommendation(
                    id="rec_observability",
                    category=RecommendationCategory.OBSERVABILITY,
                    title="Add centralized logging and health monitoring",
                    recommendation="Ship structured logs and the existing health endpoint's status "
                    "to a managed log/metrics service.",
                    reason="Little to no observability was detected.",
                    engineering_need=(
                        "Recommended: failures are otherwise invisible after deployment."
                    ),
                    learning_value="Foundation for the troubleshooting workflow.",
                    reliability_impact="Enables detecting a failed deployment automatically.",
                )
            )

        return tuple(recs)

    def _kubernetes_recommendation(
        self,
        assessment: ProjectAssessment,
        *,
        cost_priority: CostPriority,
        wants_kubernetes_experience: bool,
    ) -> Recommendation | None:
        workload_needs_k8s = False  # a single stateless API at this scale does not, by default

        if workload_needs_k8s:
            need = KubernetesNeed.REQUIRED
        elif wants_kubernetes_experience:
            need = KubernetesNeed.LEARNING_ONLY
        else:
            need = KubernetesNeed.NOT_RECOMMENDED

        if need is KubernetesNeed.NOT_RECOMMENDED and not wants_kubernetes_experience:
            return Recommendation(
                id="rec_no_kubernetes",
                category=RecommendationCategory.KUBERNETES,
                title="Do not use Kubernetes for this workload",
                recommendation="Use a simpler managed container platform instead of Kubernetes.",
                reason="This is a single low-traffic stateless API; Kubernetes-level orchestration "
                "is not required at this scale.",
                alternatives=(
                    RecommendationAlternative(
                        option="Deploy to AKS anyway",
                        why_not_preferred="Adds cluster operational overhead with no matching "
                        "workload need.",
                    ),
                ),
                engineering_need="Kubernetes is unnecessary for this workload as analyzed.",
                learning_value="",
                complexity_impact="Avoids unnecessary orchestration complexity.",
                cost_impact="Lower likely cost than a managed cluster.",
            )

        cost_note = (
            "Lower operational overhead than a managed cluster."
            if cost_priority is CostPriority.LOWEST_COST
            else "Comparable managed-service reliability without cluster operations."
        )
        return Recommendation(
            id="rec_kubernetes",
            category=RecommendationCategory.KUBERNETES,
            title="Use Kubernetes as a learning architecture",
            recommendation="Deploy the practical architecture first, then optionally add a "
            "Kubernetes learning variant.",
            reason="Kubernetes is not strictly required for this workload's current size, but you "
            "listed it as a learning objective.",
            alternatives=(
                RecommendationAlternative(
                    option="Use Kubernetes directly for this project",
                    why_not_preferred="Works, but exceeds the application's current operational "
                    "needs; document that explicitly if chosen.",
                ),
            ),
            recommended_option=(
                "Build the practical architecture first, then create a Kubernetes variant"
            ),
            engineering_need="Not required by the workload as analyzed.",
            learning_value="Directly satisfies the stated learning objective.",
            cost_impact=cost_note,
            complexity_impact="Adds cluster concepts (Pods, Deployments, probes) beyond what the "
            "workload needs on its own.",
            requires_user_decision=True,
        )
