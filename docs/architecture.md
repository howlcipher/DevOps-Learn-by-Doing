# Architecture

## Shape

A modular monolith (ADR 0002), not a multi-agent swarm. One process, one composition root
(`tutor/bootstrap.py`), constructor injection throughout, no service locator.

```text
TutorOrchestrator (tutor/orchestrator.py)
    |
    +-- CurriculumService       content graph + rendering
    +-- AssessmentService       grades choice answers, delegates open answers to LLMProvider
    +-- RecommendationService   structured recommendations
    +-- CompetencyService       state transitions, persisted
    +-- TroubleshootingService  the one V1 failure scenario
    +-- ProjectService          learner artifacts + tool calls
    +-- ToolService             the only entry point into any Tool
    +-- LLMProvider             MockLLMProvider (default) or AnthropicProvider
    +-- SessionService          session lifecycle (added beyond the spec's 8; see ADR 0002)
    +-- LearningJournal         append-only event recording (same reason)
```

Every orchestrator method takes the current `LearningSession` and returns a `TurnResult`
carrying the (possibly updated) session; the orchestrator holds no state of its own between
calls. `cli/session_loop.py` threads that session through repeated calls.

## Layers

```text
domain/            plain dataclasses and enums; no behavior, no I/O
curriculum/         content graph + the assistance/depth rendering rules
competencies/       state machine rules + persistence-backed service
learning/            session lifecycle, event journal, attempt/hint tracking, sqlite repositories
tools/               the controlled tool interface + simulated implementations
troubleshooting/     the one V1 failure scenario's content and flow
ai/                  LLMProvider abstraction + Mock/Anthropic implementations
cloud/, languages/   concept-first extension points (Azure/Python implemented; others stubs)
tutor/               the orchestrator + composition root
cli/                 argparse commands, the interactive loop, presenters
workflows/           small glue functions composing 2-3 services for one specific sequence
```

Dependencies point one direction: `domain` depends on nothing else in the package;
`curriculum`/`competencies`/`tools`/`ai` depend only on `domain`; `learning` depends on
`domain`; higher-level services (`assessments`, `recommendations`, `troubleshooting`,
`projects`) depend on the lower-tier services above; `tutor` depends on everything;
`cli` depends only on `tutor` and `domain`.

## Persistence

stdlib `sqlite3`, no ORM (see the persistence decision in the implementation plan and
`learning/persistence/schema.sql`). All SQL is confined to `learning/persistence/repositories/`;
every other layer works with plain dataclasses.

## Safety

`ToolService.invoke` is the only way to call a `Tool`; destructive operations require human
approval enforced structurally, not by convention. See docs/safety.md.

## Where to look for more detail

- docs/learning-model.md: assistance levels, explanation depth, hints, competencies.
- docs/cloud-model.md: the concept-first multi-cloud abstraction.
- docs/safety.md: simulation vs. real execution, approval gating.
- docs/adr/: the reasoning behind each of the above.
