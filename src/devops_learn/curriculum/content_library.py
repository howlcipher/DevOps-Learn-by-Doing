"""Assembles the V1 curriculum content: the Python API Platform project."""

from __future__ import annotations

from devops_learn.curriculum.modules import (
    module_01_understand_workload,
    module_02_containerize,
    module_03_troubleshoot_failure,
    module_04_terraform_plan,
    module_05_kubernetes_overview,
)
from devops_learn.domain.curriculum_models import LearningProject
from devops_learn.domain.enums import CloudProviderKind, LanguageTrackKind

API_PLATFORM_PROJECT_ID = "api_platform"


def build_api_platform_project() -> LearningProject:
    return LearningProject(
        id=API_PLATFORM_PROJECT_ID,
        title="Production-Style API Platform",
        description=(
            "Build and operate a small Python API end to end: from a local FastAPI app "
            "through containerization, infrastructure as code, Kubernetes concepts, an "
            "intentional failure, and troubleshooting."
        ),
        cloud=CloudProviderKind.AZURE,
        language=LanguageTrackKind.PYTHON,
        modules=(
            module_01_understand_workload.build_module(),
            module_02_containerize.build_module(),
            module_03_troubleshoot_failure.build_module(),
            module_04_terraform_plan.build_module(),
            module_05_kubernetes_overview.build_module(),
        ),
    )
