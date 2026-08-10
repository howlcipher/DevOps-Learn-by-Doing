# ADR 0004: Project based learning

## Status

Accepted.

## Context

The platform could teach DevOps as a sequence of independent topic lessons (Docker in
isolation, Terraform in isolation, Kubernetes in isolation) or as one continuous project
the learner builds and operates end to end. Independent topic lessons are simpler to author
and let a learner skip around, but they let a learner memorize a topic without ever seeing
how it fits into a real system, and they cannot teach troubleshooting realistically, since
a realistic failure depends on the state a real system accumulated.

## Decision

V1 implements a single continuous project, the Production-Style API Platform, that a learner
builds and operates through Git, tests, Docker, CI, Terraform, Azure, and Kubernetes in
sequence. Later modules assume the artifacts and understanding built in earlier modules.
Topic coverage (e.g. Docker) is taught only in the context this project creates for it, not
as a standalone lesson.

## Consequences

Content authoring is more expensive per topic, since every lesson must fit a continuous
narrative rather than standing alone. In exchange, the troubleshooting scenario, the
Terraform plan lesson, and later Kubernetes modules can reference a shared, believable system
instead of a synthetic example invented just for that lesson. A learner who finishes the
project has operated one real system rather than sampled several toy ones.

## Alternatives considered

Independent topic modules (a "Docker 101," a "Terraform 101," etc.) were rejected for V1
because they cannot support a believable end to end troubleshooting or rollback scenario, and
because the product's stated goal is operating real systems, not surveying tools.
