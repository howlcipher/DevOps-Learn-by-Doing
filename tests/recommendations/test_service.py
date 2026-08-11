from devops_learn.domain.analysis_models import ProjectAssessment
from devops_learn.domain.enums import CostPriority, LanguageKind, MaturityStatus
from devops_learn.recommendations.service import RecommendationService
from devops_learn.requirements.service import RequirementsService


def _assessment(**overrides: object) -> ProjectAssessment:
    defaults: dict[str, object] = dict(
        root_path="/tmp/x",
        application_type="FastAPI HTTP API",
        language=LanguageKind.PYTHON,
        framework="FastAPI",
        containerization_status=MaturityStatus.MISSING,
        ci_cd_status=MaturityStatus.MISSING,
        iac_status=MaturityStatus.MISSING,
        cloud_status=MaturityStatus.MISSING,
        healthcheck_status=MaturityStatus.GOOD,
        test_status=MaturityStatus.PARTIAL,
        observability_status=MaturityStatus.MISSING,
    )
    defaults.update(overrides)
    return ProjectAssessment(**defaults)  # type: ignore[arg-type]


def test_recommends_against_kubernetes_when_not_a_learning_objective() -> None:
    assessment = _assessment()
    requirements = RequirementsService().detect(assessment)
    recs = RecommendationService().build_recommendations(
        assessment,
        requirements,
        cost_priority=CostPriority.BALANCED,
        wants_kubernetes_experience=False,
    )
    k8s = next(r for r in recs if r.category.value == "kubernetes")
    assert k8s.id == "rec_no_kubernetes"
    assert (
        "not required" in k8s.engineering_need.lower()
        or "unnecessary" in k8s.engineering_need.lower()
    )


def test_recommends_kubernetes_as_learning_only_when_requested() -> None:
    assessment = _assessment()
    requirements = RequirementsService().detect(assessment)
    recs = RecommendationService().build_recommendations(
        assessment,
        requirements,
        cost_priority=CostPriority.BALANCED,
        wants_kubernetes_experience=True,
    )
    k8s = next(r for r in recs if r.category.value == "kubernetes")
    assert k8s.id == "rec_kubernetes"
    assert k8s.learning_value
    assert k8s.requires_user_decision is True


def test_engineering_need_and_learning_value_are_tracked_separately() -> None:
    assessment = _assessment()
    requirements = RequirementsService().detect(assessment)
    recs = RecommendationService().build_recommendations(
        assessment,
        requirements,
        cost_priority=CostPriority.BALANCED,
        wants_kubernetes_experience=True,
    )
    k8s = next(r for r in recs if r.id == "rec_kubernetes")
    assert "not required" in k8s.engineering_need.lower()
    assert "learning objective" in k8s.learning_value.lower()
