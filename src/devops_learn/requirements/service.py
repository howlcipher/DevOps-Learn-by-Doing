"""RequirementsService: infers likely DevOps requirements from a ProjectAssessment.

Table-driven and deterministic on purpose (see docs/adr/0008-structured-ai-output.md):
a requirement is either observed directly from the assessment (high confidence)
or inferred (lower confidence, tracked as is_assumption).
"""

from __future__ import annotations

from devops_learn.domain.analysis_models import ProjectAssessment
from devops_learn.domain.enums import MaturityStatus
from devops_learn.domain.requirements_models import DetectedRequirement


class RequirementsService:
    def detect(self, assessment: ProjectAssessment) -> tuple[DetectedRequirement, ...]:
        requirements: list[DetectedRequirement] = []

        if assessment.containerization_status is MaturityStatus.MISSING:
            requirements.append(
                DetectedRequirement(
                    id="containerization",
                    title="Container deployment",
                    rationale="No Dockerfile was found; a repeatable runtime artifact is needed "
                    "before this can run identically in CI and in the cloud.",
                    confidence=0.95,
                )
            )
        if assessment.ci_cd_status is MaturityStatus.MISSING:
            requirements.append(
                DetectedRequirement(
                    id="ci_cd",
                    title="CI/CD",
                    rationale="No GitHub Actions workflows were found; changes currently require "
                    "manual testing and deployment.",
                    confidence=0.9,
                )
            )
        if assessment.iac_status is MaturityStatus.MISSING:
            requirements.append(
                DetectedRequirement(
                    id="iac",
                    title="Infrastructure as Code",
                    rationale="No Terraform configuration was found; any cloud resources would "
                    "currently have to be created and tracked by hand.",
                    confidence=0.85,
                )
            )
        if assessment.database_dependencies:
            requirements.append(
                DetectedRequirement(
                    id="managed_database",
                    title="Managed database",
                    rationale=(
                        f"The project depends on {', '.join(assessment.database_dependencies)}; "
                        "a managed offering avoids operating that database by hand."
                    ),
                    confidence=0.8,
                )
            )
        if assessment.secret_indicators:
            requirements.append(
                DetectedRequirement(
                    id="secret_management",
                    title="Managed secret storage",
                    rationale=(
                        f"{len(assessment.secret_indicators)} likely secret(s) are read from the "
                        "environment; these need centralized, access-controlled storage once "
                        "deployed."
                    ),
                    confidence=0.85,
                )
            )
        if assessment.observability_status is not MaturityStatus.GOOD:
            requirements.append(
                DetectedRequirement(
                    id="observability",
                    title="Logging / monitoring",
                    rationale="Little to no structured logging or metrics collection was found.",
                    confidence=0.6,
                    is_assumption=True,
                )
            )
        if assessment.cloud_status is MaturityStatus.MISSING:
            requirements.append(
                DetectedRequirement(
                    id="cloud_deployment",
                    title="Cloud deployment",
                    rationale=(
                        "No cloud infrastructure was found; the project appears to run only "
                        "locally."
                    ),
                    confidence=0.7,
                    is_assumption=True,
                )
            )
        if assessment.framework is not None:
            requirements.append(
                DetectedRequirement(
                    id="public_access",
                    title="External HTTPS access",
                    rationale=f"{assessment.framework} is present, suggesting this is meant to be "
                    "reachable as an HTTP API.",
                    confidence=0.55,
                    is_assumption=True,
                )
            )

        return tuple(requirements)
