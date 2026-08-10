# ADR 0001: CLI first

## Status

Accepted.

## Context

V1 needs one interface that can demonstrate the full tutor experience (explanation, prediction,
hints, troubleshooting, tool actions, approval gating) without building a web frontend, an
authentication layer, or a hosted backend first. The product's actual subject matter, DevOps
and platform engineering, is itself terminal-native: the learner already needs a shell for
Docker, Terraform, and kubectl, so a CLI is not a compromise interface for this audience, it is
the natural one.

## Decision

The only interface in V1 is a CLI (`devops-learn start|resume|progress|projects|competencies|
explain`), implemented with stdlib `argparse` (see the CLI argument parsing decision recorded
in the implementation plan) plus a custom interactive loop (cli/session_loop.py) for the
turn-by-turn tutor dialogue. No web UI, no API server, no authentication layer exists in V1.

## Consequences

Every product mechanic (assistance levels, explanation depth, hints, predictions,
troubleshooting, tool approval) had to be provable in a terminal, which kept the domain model
and services (curriculum, competencies, tools, troubleshooting) fully decoupled from any
particular presentation layer; cli/presenters.py is the only place that formats text for a
screen. That decoupling is what would make a future web or IDE-integrated frontend an additive
change, not a rewrite, since `TutorOrchestrator` already returns structured `TurnResult`
values rather than pre-rendered strings.

## Alternatives considered

A minimal web UI was rejected for V1: it would have pulled focus into frontend framework
choices, auth, and hosting before the tutoring mechanics themselves were proven out, which the
"do not overbuild V1" constraint explicitly warns against. A chat-only interface (freeform text
in, freeform text out) was rejected because core logic must not be built around parsing
arbitrary chat text; the CLI's lettered menus and typed commands keep the human-facing surface
structured without needing an LLM in the loop for every interaction.
