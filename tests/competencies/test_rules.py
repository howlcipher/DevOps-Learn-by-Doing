import pytest

from devops_learn.competencies.rules import (
    next_state,
    state_for_content_viewed,
    state_for_task_outcome,
)
from devops_learn.domain.enums import CompetencyState, TaskOutcome


def test_viewing_content_never_exceeds_introduced() -> None:
    assert state_for_content_viewed() == CompetencyState.INTRODUCED


class TestStateForTaskOutcome:
    def test_unhinted_success_is_demonstrated(self) -> None:
        state = state_for_task_outcome(TaskOutcome.SUCCESS, hints_used=0, total_hints=3)
        assert state == CompetencyState.DEMONSTRATED

    def test_partially_hinted_success_is_practiced(self) -> None:
        state = state_for_task_outcome(TaskOutcome.SUCCESS, hints_used=1, total_hints=3)
        assert state == CompetencyState.PRACTICED

    def test_fully_hinted_success_is_only_guided(self) -> None:
        state = state_for_task_outcome(TaskOutcome.SUCCESS, hints_used=3, total_hints=3)
        assert state == CompetencyState.GUIDED

    @pytest.mark.parametrize("outcome", [TaskOutcome.PARTIAL, TaskOutcome.FAILED])
    def test_non_success_outcomes_cap_at_guided(self, outcome: TaskOutcome) -> None:
        state = state_for_task_outcome(outcome, hints_used=0, total_hints=3)
        assert state == CompetencyState.GUIDED


class TestNextState:
    def test_forward_progress_is_applied(self) -> None:
        assert next_state(CompetencyState.INTRODUCED, CompetencyState.PRACTICED) == (
            CompetencyState.PRACTICED
        )

    def test_a_worse_later_attempt_does_not_erase_a_prior_success(self) -> None:
        assert next_state(CompetencyState.DEMONSTRATED, CompetencyState.GUIDED) == (
            CompetencyState.DEMONSTRATED
        )

    def test_equal_candidate_is_a_no_op(self) -> None:
        assert next_state(CompetencyState.PRACTICED, CompetencyState.PRACTICED) == (
            CompetencyState.PRACTICED
        )
