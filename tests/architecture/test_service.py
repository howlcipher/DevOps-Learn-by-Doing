from devops_learn.architecture.service import ArchitectureService
from devops_learn.cloud.azure.provider import AzureProvider
from devops_learn.domain.enums import KubernetesNeed, RecommendationCategory
from devops_learn.domain.recommendation_models import Recommendation


def _rec(id: str, category: RecommendationCategory, **kwargs: object) -> Recommendation:
    return Recommendation(
        id=id,
        category=category,
        title=id,
        recommendation="",
        reason="",
        **kwargs,  # type: ignore[arg-type]
    )


def test_proposal_excludes_kubernetes_when_not_recommended() -> None:
    service = ArchitectureService(AzureProvider())
    proposal = service.propose((_rec("rec_no_kubernetes", RecommendationCategory.KUBERNETES),))
    assert proposal.kubernetes_used is False
    assert proposal.kubernetes_need is KubernetesNeed.NOT_RECOMMENDED
    assert "AKS" not in " ".join(proposal.pipeline)


def test_proposal_includes_kubernetes_and_learning_rationale_when_accepted() -> None:
    service = ArchitectureService(AzureProvider())
    proposal = service.propose(
        (_rec("rec_kubernetes", RecommendationCategory.KUBERNETES, learning_value="Teaches pods."),)
    )
    assert proposal.kubernetes_used is True
    assert proposal.kubernetes_need is KubernetesNeed.LEARNING_ONLY
    assert proposal.learning_rationale == "Teaches pods."
    assert proposal.simpler_alternative is not None
