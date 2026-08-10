"""The only fully implemented CloudProvider in V1, entirely simulated."""

from __future__ import annotations

from devops_learn.cloud.base.concepts import CloudConcept
from devops_learn.cloud.base.provider import CloudProvider
from devops_learn.domain.enums import CloudProviderKind

_SERVICE_NAMES: dict[CloudConcept, str] = {
    CloudConcept.MANAGED_KUBERNETES: "AKS (Azure Kubernetes Service)",
    CloudConcept.CONTAINER_REGISTRY: "ACR (Azure Container Registry)",
    CloudConcept.VIRTUAL_NETWORK: "Azure Virtual Network (VNet)",
    CloudConcept.MANAGED_IDENTITY: "Azure Managed Identity",
    CloudConcept.SECRETS_STORE: "Azure Key Vault",
    CloudConcept.OBJECT_STORAGE: "Azure Blob Storage",
    CloudConcept.LOG_ANALYTICS: "Azure Monitor / Log Analytics",
    CloudConcept.RESOURCE_GROUP: "Azure Resource Group",
}

_DESCRIPTIONS: dict[CloudConcept, str] = {
    CloudConcept.MANAGED_KUBERNETES: (
        "A managed control plane; Azure operates the Kubernetes API server so you only "
        "manage node pools and workloads."
    ),
    CloudConcept.CONTAINER_REGISTRY: "Stores the images your CI pipeline builds and AKS pulls.",
    CloudConcept.VIRTUAL_NETWORK: "Defines the private address space your resources live in.",
    CloudConcept.MANAGED_IDENTITY: (
        "Lets a resource authenticate to other Azure services without a stored credential."
    ),
    CloudConcept.SECRETS_STORE: "Centralized, access-controlled storage for secrets and keys.",
    CloudConcept.OBJECT_STORAGE: "Durable storage for unstructured data such as artifacts.",
    CloudConcept.LOG_ANALYTICS: "Collects logs and metrics for querying and alerting.",
    CloudConcept.RESOURCE_GROUP: "The container every other resource in this project belongs to.",
}


class AzureProvider(CloudProvider):
    @property
    def kind(self) -> CloudProviderKind:
        return CloudProviderKind.AZURE

    @property
    def is_available(self) -> bool:
        return True

    def service_name_for(self, concept: CloudConcept) -> str:
        return _SERVICE_NAMES[concept]

    def describe_concept(self, concept: CloudConcept) -> str:
        return _DESCRIPTIONS[concept]
