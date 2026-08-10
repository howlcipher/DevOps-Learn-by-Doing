# ADR 0002: Modular monolith

## Status

Accepted.

## Context

The product spec names eight collaborators (CurriculumService, AssessmentService,
RecommendationService, CompetencyService, TroubleshootingService, ProjectService, ToolService,
LLMProvider) under a single TutorOrchestrator, and explicitly warns against "a complicated
swarm of autonomous agents." The system needs enough structure to keep those eight concerns
separated without paying the operational cost of running them as separate services.

## Decision

`TutorOrchestrator` (tutor/orchestrator.py) is a single-process coordinator built with
constructor injection: every collaborator is passed in explicitly, none of them import or
depend on the orchestrator itself, and the composition root (tutor/bootstrap.py) is the only
place concrete implementations are wired together. Two collaborators beyond the eight named in
the spec were added: `SessionService` and `LearningJournal`, because `begin_project`, `resume`,
and `advance` cannot manage session lifecycle or emit audit events without them. This is
recorded here rather than left implicit, since it is a deliberate, minor extension of the
spec's architecture diagram, not a scope change: the orchestrator still has no logic of its
own beyond dispatch, and each added collaborator is a single-purpose, already-tested unit
(learning/session_service.py, learning/journal.py).

## Consequences

Every orchestrator method is a thin dispatcher: it looks up curriculum content, delegates to
exactly one or two services, and returns a `TurnResult`. This keeps `tests/tutor/
test_orchestrator_wiring.py` and the transcript-shape test able to exercise real behavior
through the same object the CLI uses, with no network calls or process boundaries in the way.
The cost is that `TutorOrchestrator`'s constructor is comparatively large (eleven
collaborators); this was judged acceptable because each one is independently simple and
independently tested, which is the actual definition of "modular" this ADR is choosing over a
literal single god-object.

## Alternatives considered

A multi-agent architecture (one LLM-driven agent per service) was rejected outright per the
spec's explicit instruction and because it would make deterministic behaviors, like "a wrong
diagnosis never advances competency," depend on agent coordination instead of plain method
calls. Splitting the eight services into separately deployed processes was rejected as
premature: V1 is a local, single-user CLI tool with no scaling or multi-tenant requirement that
would justify that operational cost.
