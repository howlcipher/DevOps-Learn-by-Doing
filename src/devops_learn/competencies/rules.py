"""Pure, table-driven rules for competency state transitions.

DEMONSTRATED requires an independent, correct, unhinted success. Viewing
content only ever reaches INTRODUCED, never higher, no matter how thoroughly
it was read. States only ever move forward: a later failed attempt does not
erase an earlier demonstrated success.
"""

from __future__ import annotations

from devops_learn.domain.enums import CompetencyState, TaskOutcome


def state_for_content_viewed() -> CompetencyState:
    return CompetencyState.INTRODUCED


def state_for_task_outcome(
    outcome: TaskOutcome, *, hints_used: int, total_hints: int
) -> CompetencyState:
    if outcome == TaskOutcome.SUCCESS:
        if hints_used == 0:
            return CompetencyState.DEMONSTRATED
        if total_hints > 0 and hints_used < total_hints:
            return CompetencyState.PRACTICED
        return CompetencyState.GUIDED
    # PARTIAL or FAILED: real engagement happened, but not a clean success.
    return CompetencyState.GUIDED


def next_state(current: CompetencyState, candidate: CompetencyState) -> CompetencyState:
    return candidate if candidate > current else current
