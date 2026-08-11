"""The proposed architecture: see architecture/service.py.

ArchitectureComponent.concept links back to cloud/base/concepts.py so the
same proposal can later be re-rendered against a different CloudProvider
without re-deriving which concepts are needed.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from devops_learn.cloud.base.concepts import CloudConcept
from devops_learn.domain.enums import CloudProviderKind, KubernetesNeed


@dataclass(frozen=True)
class ArchitectureComponent:
    concept: CloudConcept
    service_name: str
    purpose: str


@dataclass(frozen=True)
class ArchitectureProposal:
    summary: str
    cloud: CloudProviderKind
    pipeline: tuple[str, ...]  # e.g. ("GitHub", "GitHub Actions", "Docker", "ACR", "AKS")
    components: tuple[ArchitectureComponent, ...] = field(default_factory=tuple)
    terraform_resources: tuple[str, ...] = field(default_factory=tuple)
    kubernetes_need: KubernetesNeed = KubernetesNeed.NOT_RECOMMENDED
    kubernetes_used: bool = False
    engineering_rationale: str = ""
    learning_rationale: str | None = None
    simpler_alternative: str | None = None
