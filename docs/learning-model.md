# Learning model

## Progression philosophy

AI shows, AI explains, AI helps, AI hints, AI reviews, learner performs independently. The
system optimizes for what the learner can do without the AI, not for how much the AI
automates. See docs/adr/0004-project-based-learning.md and docs/adr/0005-progressive-assistance.md.

## Assistance level x explanation depth

Two independent settings, never a duplicated content matrix. Content is authored once per
task as a list of tagged `ContentBlock`s (`domain/content.py`); `curriculum/renderer.py`
composes two pure functions to decide what a specific learner sees:

- `select_by_depth`: a monotonic threshold filter on each block's `min_depth`. Controls how
  much elaboration is shown (BRIEF < NORMAL < LEARNING < DEEP).
- `arrange_by_assistance`: controls what is shown proactively versus withheld until the
  learner asks for it or exhausts hints.

| Level | WHY | WHAT | HOW proactive | Check question timing |
|---|---|---|---|---|
| GUIDED | yes | yes | yes | after WHY/WHAT/HOW |
| ASSISTED | yes | yes | withheld | after WHY/WHAT |
| CHALLENGE | yes | yes | withheld | before WHAT (predict first) |
| INDEPENDENT | yes | withheld | withheld | before any content |

## Progressive hints

A `Task` carries an ordered `hints: tuple[Hint, ...]` ladder plus a `full_explanation` block.
`learning/attempt_tracker.py` tracks how many hints a given attempt has used and never repeats
one; `curriculum/renderer.py`'s `full_explanation_allowed` decides when the full answer may
surface without an explicit request: GUIDED after 1 hint, ASSISTED after 2, CHALLENGE only once
every hint is exhausted, INDEPENDENT never proactively. An explicit request or exhausting every
hint always unlocks it, so the learner is never stuck.

## Learn by doing loop

Introduce, explain, ask the learner to predict, learner performs the action, validate, show
the result, explain the result, offer a challenge/variation. Predictions are represented by
`domain.content.PredictionPrompt`: an open question recorded via `AssessmentService`
(ungraded, `Assessment.is_correct is None`), followed by the real `outcome_summary` so the
learner compares their guess against what actually happens.

## Competencies

18 codes (see `domain/enums.py: CompetencyCode`), each with state NOT_STARTED -> INTRODUCED ->
GUIDED -> PRACTICED -> DEMONSTRATED. See docs/adr/0008-competency-based-progress.md for the
full rationale: viewing content only ever reaches INTRODUCED; DEMONSTRATED requires an
unhinted, successful attempt; states only move forward.

## History and summaries

Every learner action is journaled as a `LearningEvent` (`learning/journal.py`), append-only,
with a monotonic `sequence_no` per session. `learning/summary_service.py` builds a
`LearningSummary` deterministically from persisted competency states and events; an
`LLMProvider` may later narrate that summary in friendlier prose, but the underlying facts
always come from the database, never from the model.

## Session persistence

`learning_sessions.current_module_id/current_lesson_id/current_task_id` is the live resume
pointer; `devops-learn resume` reads it directly in O(1). `learning_events` is audit history
only; the platform never reconstructs a session's position by replaying it.
