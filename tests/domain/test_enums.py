from devops_learn.domain.enums import AssistanceLevel, CompetencyState, ExplanationDepth


def test_assistance_level_is_ordered_most_support_first() -> None:
    assert AssistanceLevel.GUIDED < AssistanceLevel.ASSISTED
    assert AssistanceLevel.ASSISTED < AssistanceLevel.CHALLENGE
    assert AssistanceLevel.CHALLENGE < AssistanceLevel.INDEPENDENT


def test_explanation_depth_is_ordered_least_to_most() -> None:
    assert ExplanationDepth.BRIEF < ExplanationDepth.NORMAL
    assert ExplanationDepth.NORMAL < ExplanationDepth.LEARNING
    assert ExplanationDepth.LEARNING < ExplanationDepth.DEEP


def test_competency_state_is_ordered_and_demonstrated_is_highest() -> None:
    assert CompetencyState.NOT_STARTED < CompetencyState.INTRODUCED
    assert CompetencyState.DEMONSTRATED == max(CompetencyState)
