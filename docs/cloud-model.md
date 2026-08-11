# Cloud model

See docs/adr/0005-concept-first-multi-cloud.md for the full rationale.

## Concept first

`ArchitectureService` reasons in terms of `CloudConcept` (`cloud/base/concepts.py`):
MANAGED_KUBERNETES, CONTAINER_REGISTRY, VIRTUAL_NETWORK, MANAGED_IDENTITY, SECRETS_STORE,
OBJECT_STORAGE, LOG_ANALYTICS, RESOURCE_GROUP. Each `CloudProvider` implementation maps every
concept to its own service name and a short, provider-specific explanation. Concept to
provider, never provider to provider: nothing assumes Azure, AWS, and GCP are interchangeable.

| Concept | Azure |
|---|---|
| Managed Kubernetes | AKS (Azure Kubernetes Service) |
| Container registry | ACR (Azure Container Registry) |
| Virtual network | Azure Virtual Network (VNet) |
| Managed identity | Azure Managed Identity |
| Secrets store | Azure Key Vault |
| Object storage | Azure Blob Storage |
| Log analytics | Azure Monitor / Log Analytics |
| Resource group | Azure Resource Group |

## What is implemented

`AzureProvider` (`cloud/azure/provider.py`) is the only `is_available = True` provider in V1,
and it is entirely simulated (see docs/safety.md). `AWSProvider` and `GCPProvider` declare
`is_available = False` and raise `ComingSoonError` from every other method rather than
returning a fabricated mapping.

## Language support

`ProjectAnalyzer` detects `LanguageKind.PYTHON` (via `pyproject.toml`/`requirements.txt`/`*.py`)
and `LanguageKind.GO` (via `go.mod`) today; Python is the only fully supported track with a
bundled example project (`projects/api_platform/`). Go detection exists as a clean extension
point without a bundled example yet.

## Adding a provider later

Implement the `CloudProvider` interface (`cloud/base/provider.py`) for the new provider, set
`is_available = True`, and map every existing `CloudConcept`. No change to
`ArchitectureService` or to the concept vocabulary itself should be required; if a concept
genuinely does not translate to a given cloud, add a new, honestly-scoped concept rather than
stretching an existing one.
