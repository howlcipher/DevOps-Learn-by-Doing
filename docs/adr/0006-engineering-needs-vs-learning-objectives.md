# ADR 0006: Engineering needs vs. learning objectives

## Status

Accepted.

## Context

A platform that only ever recommends "what the user asked to learn" gives bad engineering
advice. A platform that only ever recommends "what the workload strictly needs" cannot serve the
stated goal of teaching Kubernetes, Terraform, etc. through real work. Conflating the two
justifications hides which one is actually driving a given recommendation.

## Decision

`Recommendation` (`domain/recommendation_models.py`) carries `engineering_need` and
`learning_value` as separate fields, always. `RecommendationService._kubernetes_recommendation`
is the concrete implementation of this: it independently computes whether the *workload* needs
Kubernetes and whether the user stated a *learning objective* for it, and produces different
recommendations (`rec_no_kubernetes` vs. `rec_kubernetes`) depending on the combination, always
stating the engineering conclusion honestly even when a learning objective changes what gets
built.

## Alternatives

- **A single "reason" field.** Rejected: makes it impossible to later ask "was this actually
  necessary?" separately from "did this serve what I wanted to learn?" — both real, separate
  questions the product spec asks the platform to be able to answer.

## Consequences

- The platform can say "Kubernetes is unnecessary for this workload, but you asked to learn it,"
  and a Review-mode audit of an existing project never inflates engineering necessity to justify
  a technology someone happened to want to learn.
