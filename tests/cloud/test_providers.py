import pytest

from devops_learn.cloud.aws.provider import AWSProvider
from devops_learn.cloud.azure.provider import AzureProvider
from devops_learn.cloud.base.concepts import CloudConcept
from devops_learn.cloud.gcp.provider import GCPProvider
from devops_learn.domain.enums import CloudProviderKind
from devops_learn.errors import ComingSoonError


def test_azure_is_available_and_maps_every_concept() -> None:
    provider = AzureProvider()
    assert provider.is_available is True
    assert provider.kind == CloudProviderKind.AZURE
    for concept in CloudConcept:
        assert provider.service_name_for(concept)
        assert provider.describe_concept(concept)


def test_azure_managed_kubernetes_maps_to_aks() -> None:
    provider = AzureProvider()
    assert "AKS" in provider.service_name_for(CloudConcept.MANAGED_KUBERNETES)


@pytest.mark.parametrize("provider_cls", [AWSProvider, GCPProvider])
def test_unavailable_providers_declare_themselves_and_raise_coming_soon(
    provider_cls: type,
) -> None:
    provider = provider_cls()
    assert provider.is_available is False
    with pytest.raises(ComingSoonError):
        provider.service_name_for(CloudConcept.MANAGED_KUBERNETES)
    with pytest.raises(ComingSoonError):
        provider.describe_concept(CloudConcept.MANAGED_KUBERNETES)
