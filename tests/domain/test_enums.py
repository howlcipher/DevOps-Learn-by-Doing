from devops_learn.domain.enums import ExperienceState, ExplanationDepth, OperatingMode


def test_explanation_depth_is_ordered_least_to_most() -> None:
    assert ExplanationDepth.BRIEF < ExplanationDepth.NORMAL
    assert ExplanationDepth.NORMAL < ExplanationDepth.LEARNING
    assert ExplanationDepth.LEARNING < ExplanationDepth.DEEP


def test_operating_mode_has_the_four_documented_modes() -> None:
    assert {m.value for m in OperatingMode} == {"learn", "collaborate", "autopilot", "review"}


def test_experience_state_never_implies_certification_language() -> None:
    names = {s.name for s in ExperienceState}
    assert "DEMONSTRATED" in names
    assert not any("CERTIFIED" in name or "MASTERED" in name for name in names)
