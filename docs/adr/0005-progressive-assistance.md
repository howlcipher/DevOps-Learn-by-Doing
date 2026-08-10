# ADR 0005: Progressive assistance as content rendering, not content duplication

## Status

Accepted.

## Context

Assistance level (GUIDED, ASSISTED, CHALLENGE, INDEPENDENT) and explanation depth (BRIEF,
NORMAL, LEARNING, DEEP) both need to change what a lesson shows, without either axis
duplicating curriculum content. The naive approach, authoring sixteen variants per lesson
(four levels times four depths), does not scale past a handful of lessons and creates a
constant risk of the variants drifting out of sync with each other.

## Decision

Curriculum content is authored once per lesson/task as a list of tagged ContentBlocks (see
domain/content.py). Two independent, pure functions compose to decide what a specific learner
sees: select_by_depth filters blocks by a monotonic ExplanationDepth threshold on each block's
min_depth; arrange_by_assistance partitions the remaining blocks into what is shown proactively
versus what is withheld until the learner requests it or exhausts hints, per AssistanceLevel.
See curriculum/renderer.py for the concrete rule table (roughly eight small rules instead of
sixteen content variants) and the separate hint-escalation gate, full_explanation_allowed.

## Consequences

Content authors write one block list per task and never think about the sixteen
level-times-depth combinations directly; the two composed functions are unit tested against
the rule table instead. Adding a fifth assistance level or depth in the future means extending
two small functions, not rewriting every lesson. The tradeoff is that content authors must
tag each block correctly (min_depth, always_include, kind) for the composition to behave as
intended; getting a tag wrong silently changes rendering behavior rather than raising an error,
which is why tests/curriculum/test_content_library_integrity.py exists.

## Alternatives considered

Per-level content variants were rejected as an authoring and maintenance burden that scales
with the number of lessons. A single LLM call at render time to "adjust" one canonical version
was rejected because it would make core tutoring behavior depend on non-deterministic model
output rather than testable business logic, violating the constraint that core logic must not
be built around parsing or generating arbitrary text.
