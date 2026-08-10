"""Extension point only. Not implemented in V1: see docs/roadmap.md."""

from __future__ import annotations

from devops_learn.cloud.base.concepts import CloudConcept
from devops_learn.cloud.base.provider import CloudProvider
from devops_learn.domain.enums import CloudProviderKind
from devops_learn.errors import ComingSoonError


class GCPProvider(CloudProvider):
    @property
    def kind(self) -> CloudProviderKind:
        return CloudProviderKind.GCP

    @property
    def is_available(self) -> bool:
        return False

    def service_name_for(self, concept: CloudConcept) -> str:
        raise ComingSoonError("GCP is not implemented yet. Azure is the V1 cloud path.")

    def describe_concept(self, concept: CloudConcept) -> str:
        raise ComingSoonError("GCP is not implemented yet. Azure is the V1 cloud path.")
