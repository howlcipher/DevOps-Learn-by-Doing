from devops_learn.domain.enums import ExecutionMode, ExperienceState, ExplanationDepth


def test_explanation_depth_is_ordered_least_to_most() -> None:
    assert ExplanationDepth.BRIEF < ExplanationDepth.NORMAL
    assert ExplanationDepth.NORMAL < ExplanationDepth.LEARNING
    assert ExplanationDepth.LEARNING < ExplanationDepth.DEEP


def test_execution_mode_has_the_five_documented_modes() -> None:
    assert {m.value for m in ExecutionMode} == {
        "observe",
        "guided",
        "collaborative",
        "ai_executed",
        "autonomous",
    }


def test_experience_state_never_implies_certification_language() -> None:
    names = {s.name for s in ExperienceState}
    assert "DEMONSTRATED" in names
    assert not any("CERTIFIED" in name or "MASTERED" in name for name in names)
