"""ArchitectureService: turns recommendations into one concrete, explained
architecture proposal for a specific CloudProvider.

Concept-first (see docs/adr/0005-concept-first-multi-cloud.md): components are
chosen as CloudConcept values and rendered through the injected CloudProvider,
so switching cloud only changes which provider is injected.
"""

from __future__ import annotations

from devops_learn.cloud.base.concepts import CloudConcept
from devops_learn.cloud.base.provider import CloudProvider
from devops_learn.domain.architecture_models import ArchitectureComponent, ArchitectureProposal
from devops_learn.domain.enums import KubernetesNeed
from devops_learn.domain.recommendation_models import Recommendation


class ArchitectureService:
    def __init__(self, cloud_provider: CloudProvider) -> None:
        self._cloud_provider = cloud_provider

    def propose(self, recommendations: tuple[Recommendation, ...]) -> ArchitectureProposal:
        rec_by_id = {r.id: r for r in recommendations}
        use_kubernetes = "rec_kubernetes" in rec_by_id

        concepts: list[CloudConcept] = [CloudConcept.RESOURCE_GROUP]
        if use_kubernetes:
            concepts += [
                CloudConcept.VIRTUAL_NETWORK,
                CloudConcept.MANAGED_KUBERNETES,
                CloudConcept.CONTAINER_REGISTRY,
            ]
        else:
            concepts += [CloudConcept.CONTAINER_REGISTRY]
        if "rec_secrets" in rec_by_id or "rec_remove_hardcoded_secret" in rec_by_id:
            concepts += [CloudConcept.SECRETS_STORE, CloudConcept.MANAGED_IDENTITY]
        if "rec_observability" in rec_by_id:
            concepts.append(CloudConcept.LOG_ANALYTICS)

        components = tuple(
            ArchitectureComponent(
                concept=concept,
                service_name=self._cloud_provider.service_name_for(concept),
                purpose=self._cloud_provider.describe_concept(concept),
            )
            for concept in concepts
        )

        pipeline = ["GitHub", "GitHub Actions", "Docker"]
        pipeline.append(self._cloud_provider.service_name_for(CloudConcept.CONTAINER_REGISTRY))
        if use_kubernetes:
            pipeline.append(self._cloud_provider.service_name_for(CloudConcept.MANAGED_KUBERNETES))
        else:
            pipeline.append("Managed container platform")

        if "rec_kubernetes" in rec_by_id:
            need = KubernetesNeed.LEARNING_ONLY
        elif "rec_no_kubernetes" in rec_by_id:
            need = KubernetesNeed.NOT_RECOMMENDED
        else:
            need = KubernetesNeed.OPTIONAL

        k8s_rec = rec_by_id.get("rec_kubernetes") or rec_by_id.get("rec_no_kubernetes")
        engineering_rationale = (
            k8s_rec.engineering_need if k8s_rec else "Standard container deployment."
        )
        learning_rationale = (
            rec_by_id["rec_kubernetes"].learning_value if "rec_kubernetes" in rec_by_id else None
        )
        simpler_alternative = (
            "A managed container platform (no cluster to operate) would satisfy this workload "
            "with less operational overhead."
            if use_kubernetes and need is KubernetesNeed.LEARNING_ONLY
            else None
        )

        terraform_resources = [c.concept.value for c in components]

        return ArchitectureProposal(
            summary=" -> ".join(pipeline) + " -> Application",
            cloud=self._cloud_provider.kind,
            pipeline=tuple(pipeline),
            components=components,
            terraform_resources=tuple(terraform_resources),
            kubernetes_need=need,
            kubernetes_used=use_kubernetes,
            engineering_rationale=engineering_rationale,
            learning_rationale=learning_rationale,
            simpler_alternative=simpler_alternative,
        )
