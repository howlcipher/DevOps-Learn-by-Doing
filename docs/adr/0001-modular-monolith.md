# ADR 0001: Modular monolith

## Status

Accepted.

## Context

The platform has many cohesive but distinct concerns: project analysis, requirements detection,
clarifying questions, recommendations, architecture proposals, planning, explanation, audit,
approvals, experience tracking, troubleshooting, and controlled tool execution. These need to be
reusable by more than one interface (CLI today, potentially a web UI later).

## Decision

Implement every concern as a small, focused service class within one Python package
(`devops_learn`), composed by a single composition root (`bootstrap.py`). Workflow functions
(`workflows/analyze_flow.py`) sequence these services; they contain no business logic of their
own, only ordering, and depend on an abstract `Ui` for interaction so they are not tied to the
terminal.

## Alternatives

- **Microservices per concern.** Would add deployment and network complexity with no matching
  benefit at this scale; nothing here needs independent scaling or deployment.
- **One large orchestrator class.** Rejected: it would become a god object mixing analysis,
  recommendation, and I/O concerns, which is exactly what modularity is meant to avoid.

## Consequences

- Any service can be unit tested in isolation with fakes for its dependencies.
- A future web UI reuses every service and workflow function unchanged; it only needs its own
  `Ui` implementation in place of `cli/terminal_ui.py`.
- Care is required to keep workflow functions from accumulating business logic that belongs in a
  service instead.
