# ADR 0005: Concept first, multi-cloud

## Status

Accepted.

## Context

The platform must support Azure, AWS, and GCP eventually, but should not pretend AWS and GCP are
implemented before they are, and should not hardcode Azure-specific naming into
architecture/recommendation logic.

## Decision

Model cloud capabilities as `CloudConcept` values (`cloud/base/concepts.py`): managed Kubernetes,
container registry, virtual network, managed identity, secrets store, object storage, log
analytics, resource group. `ArchitectureService` reasons entirely in terms of concepts and asks
the injected `CloudProvider` (`cloud/base/provider.py`) for the concrete service name and
description. `AzureProvider` is fully implemented in V1; `AWSProvider` and `GCPProvider` declare
`is_available=False` and raise `ComingSoonError` from every other method rather than faking
parity with Azure.

## Alternatives

- **Branch on cloud provider throughout the business logic.** Rejected: this is exactly the
  coupling concept-first abstraction avoids, and would make adding AWS/GCP support require
  touching every recommendation/architecture call site instead of one new provider class.

## Consequences

- Switching the target cloud for an existing proposal is a matter of injecting a different
  `CloudProvider`, not rewriting `ArchitectureService`.
- AWS and GCP are honest placeholders: calling their unimplemented methods fails loudly instead
  of returning plausible-looking fake data.
