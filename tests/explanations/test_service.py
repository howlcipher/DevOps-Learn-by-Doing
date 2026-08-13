from devops_learn.domain.enums import ExecutionMode, ExplanationDepth
from devops_learn.domain.explanation_models import LearningMoment
from devops_learn.explanations.service import ExplanationService


def _moment(**overrides: object) -> LearningMoment:
    defaults: dict[str, object] = dict(
        concept="Terraform state",
        trigger="before init",
        summary="State tracks what Terraform believes exists.",
        deep_explanation="Full detail about state internals.",
        why_it_matters="Understanding state matters for trustworthy plans.",
        related_artifact="docs/terraform-state.md",
    )
    defaults.update(overrides)
    return LearningMoment(**defaults)  # type: ignore[arg-type]


def test_related_artifact_is_rendered_at_learning_depth() -> None:
    rendered = ExplanationService().render_learning_moment(
        _moment(), mode=ExecutionMode.COLLABORATIVE, depth=ExplanationDepth.LEARNING
    )
    assert rendered is not None
    assert "docs/terraform-state.md" in rendered


def test_related_artifact_is_omitted_below_learning_depth() -> None:
    rendered = ExplanationService().render_learning_moment(
        _moment(), mode=ExecutionMode.COLLABORATIVE, depth=ExplanationDepth.NORMAL
    )
    assert rendered is not None
    assert "docs/terraform-state.md" not in rendered


def test_related_artifact_absent_when_not_set() -> None:
    rendered = ExplanationService().render_learning_moment(
        _moment(related_artifact=None),
        mode=ExecutionMode.COLLABORATIVE,
        depth=ExplanationDepth.DEEP,
    )
    assert rendered is not None
    assert "See:" not in rendered


def test_learning_moment_suppressed_in_autonomous_mode_below_deep_depth() -> None:
    rendered = ExplanationService().render_learning_moment(
        _moment(), mode=ExecutionMode.AUTONOMOUS, depth=ExplanationDepth.LEARNING
    )
    assert rendered is None
