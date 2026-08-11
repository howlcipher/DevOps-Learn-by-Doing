# ADR 0002: Explainable AI workflow

## Status

Accepted.

## Context

The product's central claim is that AI should make DevOps decisions understandable to the human
supervising them, not just automate the work. That requires explanation to be a first-class,
structured concept, not an incidental side effect of prose the AI happens to generate.

## Decision

Model explanations as a fixed structure (`domain/explanation_models.Explanation`): ACTION, WHY,
DECISION, ALTERNATIVES, TRADEOFF, WHAT_TO_UNDERSTAND, RESULT. `ExplanationService` renders this
structure as text, scaled by `ExecutionMode` (who performs the work) and
`ExplanationDepth` (how deep any rendered explanation goes) — two independent axes. Recurring
concept explanations that are triggered by a specific action use the related but distinct
`LearningMoment` structure.

## Alternatives

- **Let the LLM decide what to say and how much.** Rejected: produces inconsistent depth and
  makes automated testing of "did we explain this" impossible.
- **One fixed paragraph per action, never scaled.** Rejected: correctly serves Learn mode but is
  noise in Autopilot mode; the spec explicitly asks for both experiences from the same system.

## Consequences

- Every explanation call site fills in only the fields that apply; trivial actions render as one
  line rather than a padded template.
- Mode and depth can be changed independently: "AI-executed mode with deep explanations" and
  "collaborative mode with brief explanations" are both representable.
