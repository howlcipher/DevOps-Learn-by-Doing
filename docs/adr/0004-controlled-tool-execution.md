# ADR 0004: Controlled tool execution

## Status

Accepted.

## Context

The AI must be able to act (build a container, run Terraform, inspect Kubernetes) without being
given unrestricted shell access, which would make risk classification and approval gating
unenforceable in practice.

## Decision

Every capability the AI can invoke is a `Tool` (`tools/base.py`) exposing a fixed set of
`ToolOperationSpec` entries with `risk_level`, `supports_dry_run`, `requires_approval`, and
`is_destructive`. `ToolService` is the sole entry point that may call `Tool.execute`, and it
enforces approval for any operation that requires it. V1 ships `SimulatedDockerTool`,
`SimulatedTerraformTool`, `SimulatedKubernetesTool`, `SimulatedCloudTool`, `SimulatedGitTool`,
`SimulatedPythonTool`, and `SimulatedValidationTool` — all deterministic, with no real subprocess
or network calls. Milestones 1-3 (see `docs/roadmap.md`) replace these with real implementations
behind the same interface.

## Alternatives

- **Give the LLM a generic shell-execution tool.** Rejected outright per the product's safety
  requirements: risk level and approval would become a prompt convention, not an enforced
  property of the system.

## Consequences

- Adding a new capability means adding an operation to an existing `Tool` or a new `Tool`
  implementing the same interface, not widening what the AI is allowed to run arbitrarily.
- Simulation and real execution are swappable behind the same `Tool` interface; no calling code
  needs to know which is in use.
