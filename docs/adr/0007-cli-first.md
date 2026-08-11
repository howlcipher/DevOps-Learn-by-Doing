# ADR 0007: CLI first

## Status

Accepted.

## Context

The platform needs one concrete, testable interface before any web UI. It also needs its
internal services to be reusable by that future web UI without rewriting them.

## Decision

Ship a CLI (`devops-learn analyze|review|history|explain`) as the only interface in V1. CLI
command modules (`cli/commands/*.py`) are thin: they parse arguments, construct options, and call
a workflow function or service. All interaction goes through the `Ui` abstraction
(`workflows/ui.py`), implemented for the terminal by `cli/terminal_ui.py`. No workflow or service
imports anything from `cli/`.

## Alternatives

- **Build a web UI first.** Rejected for V1: substantially more surface area (auth, HTTP,
  frontend) before the core assess/recommend/build/validate loop is proven out.

## Consequences

- `analyze`, `review`, `history`, and `explain` cover the primary workflow end to end; `plan` and
  `build` are not separate commands because `analyze` already sequences planning and building
  through the same reusable services — a future web UI or a `plan`/`build` split can be added
  later without touching `workflows/analyze_flow.py`.
- A web UI can be added by writing a new `Ui` implementation and calling the same workflow
  functions; no service-layer change is required.
