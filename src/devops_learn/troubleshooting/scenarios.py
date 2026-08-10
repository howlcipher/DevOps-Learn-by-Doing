"""The one V1 end-to-end troubleshooting scenario: the container will not start.

Paired with curriculum module_03_troubleshoot_failure.py via
CONTAINER_WONT_START_SCENARIO_ID, which workflows/troubleshooting_flow.py maps
to TROUBLESHOOT_CONTAINER_WONT_START_TASK_ID.
"""

from __future__ import annotations

from devops_learn.domain.curriculum_models import Hint
from devops_learn.domain.enums import CompetencyCode
from devops_learn.domain.troubleshooting_models import (
    Diagnosis,
    EvidenceSource,
    FailureScenario,
    Resolution,
    TroubleshootingStep,
)

CONTAINER_WONT_START_SCENARIO_ID = "container_wont_start"


def build_container_wont_start_scenario() -> FailureScenario:
    step = TroubleshootingStep(
        prompt="What should you inspect?",
        sources=(
            EvidenceSource(
                id="terraform_state",
                label="Terraform state",
                evidence_text=(
                    "No resources are managed yet; this failure happens entirely on your "
                    "machine, before any cloud resource exists."
                ),
                is_relevant=False,
            ),
            EvidenceSource(
                id="container_logs",
                label="Container logs",
                evidence_text=(
                    "Error: 'PORT' environment variable is not set. Uvicorn cannot bind to "
                    "a port and the process exits immediately."
                ),
                is_relevant=True,
            ),
            EvidenceSource(
                id="dns",
                label="DNS",
                evidence_text="DNS resolution for the registry hostname succeeds normally.",
                is_relevant=False,
            ),
            EvidenceSource(
                id="kubernetes_ingress",
                label="Kubernetes ingress",
                evidence_text=(
                    "No ingress exists yet; this workload has not been deployed to "
                    "Kubernetes."
                ),
                is_relevant=False,
            ),
        ),
    )

    candidate_diagnoses = (
        Diagnosis(
            key="missing_port_env_var",
            label="Missing PORT environment variable",
            is_correct=True,
        ),
        Diagnosis(key="corrupted_image", label="The Docker image is corrupted", is_correct=False),
        Diagnosis(key="dns_failure", label="DNS resolution is failing", is_correct=False),
        Diagnosis(
            key="terraform_drift",
            label="Terraform state has drifted from reality",
            is_correct=False,
        ),
    )

    resolution = Resolution(
        diagnosis_key="missing_port_env_var",
        explanation="The application is missing the required PORT environment variable.",
        fix_summary="Set PORT in the container's environment before starting it.",
    )

    hints = (
        Hint(level=1, text="Check whether Docker created the container successfully."),
        Hint(level=2, text="Inspect the container logs."),
        Hint(level=3, text="Look for an application startup error."),
    )

    return FailureScenario(
        id=CONTAINER_WONT_START_SCENARIO_ID,
        title="The API container will not start",
        narrative="The API container will not start.",
        steps=(step,),
        candidate_diagnoses=candidate_diagnoses,
        resolution=resolution,
        competency_codes=(CompetencyCode.TROUBLESHOOTING, CompetencyCode.DOCKER),
        hints=hints,
    )
