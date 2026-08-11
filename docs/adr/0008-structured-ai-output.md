# ADR 0008: Structured AI output

## Status

Accepted.

## Context

If architecture decisions live inside LLM-generated prose, they cannot be reliably tested,
audited, or reasoned about by the rest of the system (risk classification, approval gating,
experience tracking all need typed data, not text to re-parse).

## Decision

Every decision-bearing structure — `ProjectAssessment`, `DetectedRequirement`,
`ClarifyingQuestion`, `Recommendation`, `ArchitectureProposal`, `ImplementationPlan`,
`TerraformPlanSummary`, `Diagnosis` — is a typed dataclass produced deterministically by this
platform's own services (`analysis/`, `requirements/`, `questions/`, `recommendations/`,
`architecture/`, `planning/`, `validation/`, `troubleshooting/`). `LLMProvider`
(`ai/provider.py`) is deliberately narrow: it only produces freeform prose
(`TopicExplanation`, `ArchitectureExplanation`, a narrated summary paragraph) and is never on the
path that decides what to recommend, build, or diagnose.

## Alternatives

- **Ask the LLM to return the Recommendation/ArchitectureProposal directly.** Rejected: makes the
  platform's core engineering judgment (e.g. "Kubernetes is unnecessary here") dependent on
  prompt behavior, and untestable without mocking the LLM for every decision path.

## Consequences

- `MockLLMProvider` (used by default in simulation and by the whole test suite) proves the
  platform's decisions are correct with zero AI calls; a real `AnthropicProvider` only changes
  how explanations read, never what gets decided.
- Adding a new AI provider means implementing three narrow methods, not reverse-engineering what
  shape of JSON every business rule expects back.
