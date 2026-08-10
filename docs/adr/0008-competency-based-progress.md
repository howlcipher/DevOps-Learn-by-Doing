# ADR 0008: Competency based progress

## Status

Accepted.

## Context

The platform needs a way to track what a learner actually knows how to do, separate from
what content they have merely been shown. A tempting shortcut is to mark a competency
complete once its lesson has been viewed, which is cheap to implement but does not reflect
real ability and undermines the product's stated goal: the learner should finish capable of
performing the work independently, not capable of having scrolled past an explanation of it.

## Decision

Competency state (NOT_STARTED, INTRODUCED, GUIDED, PRACTICED, DEMONSTRATED) is derived only
from learner actions with a real outcome, never from content views alone. Viewing content can
only ever reach INTRODUCED (competencies/rules.py, state_for_content_viewed). Reaching
DEMONSTRATED requires a task outcome of SUCCESS with zero hints used; PRACTICED requires a
success with some but not all available hints used; GUIDED covers a success that needed every
hint, or any non-success attempt. States only move forward (competencies/rules.py, next_state):
a later weak attempt never erases an earlier demonstrated success. Every state change is
recorded twice: as a row in competency_states (current, mutable) and as a row in
competency_transitions (append-only history), and is journaled as a COMPETENCY_ADVANCED
LearningEvent.

## Consequences

CompetencyService is a pure function of (current state, task outcome, hints used) plus simple
persistence, with no hidden heuristics or LLM judgment involved in whether a competency
advances. This makes the "viewing is not demonstrating" property directly unit testable rather
than a matter of prompt engineering. The cost is that a learner who reads every word of an
explanation but does not attempt the task will show no competency progress at all, which is
intentional given this product's goal, but should be surfaced clearly in progress summaries so
it does not read as the tool failing to notice engagement.

## Alternatives considered

Marking INTRODUCED -> DEMONSTRATED on lesson completion was rejected as exactly the shortcut
this ADR exists to avoid. An LLM-graded confidence score for "how well did the learner seem to
understand this" was rejected for V1 because it would make a core, testable progress signal
depend on non-deterministic model output instead of an observable outcome (success or failure,
hints used or not).
