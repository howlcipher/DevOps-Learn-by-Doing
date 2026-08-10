"""CloudProvider: concept -> provider implementation.

Providers that are not yet implemented (AWS, GCP in V1) declare
is_available=False and raise ComingSoonError from every other method, rather
than faking parity with Azure.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from devops_learn.cloud.base.concepts import CloudConcept
from devops_learn.domain.enums import CloudProviderKind


class CloudProvider(ABC):
    @property
    @abstractmethod
    def kind(self) -> CloudProviderKind: ...

    @property
    @abstractmethod
    def is_available(self) -> bool: ...

    @abstractmethod
    def service_name_for(self, concept: CloudConcept) -> str:
        """The provider-specific service name for a concept, e.g. 'AKS'."""

    @abstractmethod
    def describe_concept(self, concept: CloudConcept) -> str:
        """A short, provider-specific explanation of how this concept shows up here."""
