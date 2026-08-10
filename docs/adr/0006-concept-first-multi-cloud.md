# ADR 0006: Concept first, multi cloud

## Status

Accepted.

## Context

The platform must support Azure now while leaving room for AWS and GCP later, without forcing
every cloud into identical semantics. A naive multi-cloud abstraction that assumes Azure, AWS,
and GCP always have a 1:1 resource mapping teaches a false model of the world and breaks the
first time a concept does not translate cleanly.

## Decision

Teach concepts independently of provider names. `CloudConcept` (cloud/base/concepts.py) is the
vocabulary the curriculum and the learner ever have to reason about (for example
MANAGED_KUBERNETES); `CloudProvider` (cloud/base/provider.py) maps each concept to that
provider's specific service name and a short provider-specific description. `AzureProvider`
implements every concept for V1. `AWSProvider` and `GCPProvider` declare `is_available = False`
and raise `ComingSoonError` from every other method rather than returning a fabricated mapping,
so the extension point exists in the type system without pretending to be a working curriculum.

## Consequences

Adding AWS or GCP later means implementing `CloudProvider` for that provider and setting
`is_available = True`; no change to the concept vocabulary or to curriculum content that
already reasons in terms of concepts. The cost is that some cloud-specific nuance does not fit
the concept model cleanly (a service that exists on one provider with no real equivalent on
another); when that happens, the concept vocabulary should grow a new, honestly-scoped concept
rather than stretching an existing one to fit, which is a content-authoring discipline this ADR
records but cannot enforce by itself.

## Alternatives considered

A generic `dict[str, str]` mapping of resource names per provider was rejected: it is
untyped, gives no compile-time signal when a concept is missing for a provider, and invites
exactly the "Azure == AWS == GCP" assumption this ADR exists to avoid. Waiting to design the
abstraction until AWS or GCP is actually implemented was rejected because the concept
vocabulary needs to be right before curriculum content is written against it; retrofitting it
later would mean rewriting lessons.
