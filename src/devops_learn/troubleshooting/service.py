"""TroubleshootingService: gathers structured evidence before ever asking for
a diagnosis, then produces one.

Per the product spec, the AI is never handed a one-line failure description
and asked to guess: it always receives EvidenceItem entries gathered from
real (or, in simulation mode, simulated) ToolResult output first. See
docs/architecture.md#troubleshooting.
"""

from __future__ import annotations

from devops_learn.domain.troubleshooting_models import Diagnosis, EvidenceItem, FailureEvent
from devops_learn.tools.service import ToolService


class TroubleshootingService:
    def __init__(self, tool_service: ToolService) -> None:
        self._tool_service = tool_service

    def gather_evidence(self) -> FailureEvent:
        """Collects evidence for the one intentional V1 simulated failure: a pod that
        never becomes ready because its readiness probe targets the wrong path."""
        pods = self._tool_service.invoke("kubernetes", "get_pods")
        self._tool_service.invoke("kubernetes", "describe")
        logs = self._tool_service.invoke("kubernetes", "logs")

        evidence = (
            EvidenceItem(source="kubernetes.get_pods", content=pods.summary, is_relevant=False),
            EvidenceItem(
                source="kubernetes.describe",
                content=(
                    "Readiness probe failed: HTTP probe to /health/ready returned 404. "
                    "Container is Running but not Ready. (simulated)"
                ),
                is_relevant=True,
            ),
            EvidenceItem(source="kubernetes.logs", content=logs.summary, is_relevant=False),
            EvidenceItem(
                source="kubernetes.service_selector",
                content=(
                    "Service selector: app=api-platform. Pod label: app=api-platform. "
                    "Selector matches; traffic routing is not the cause. (simulated)"
                ),
                is_relevant=False,
            ),
        )
        return FailureEvent(
            title="Deployment did not become ready",
            narrative=(
                "The rollout completed but the pod never reports Ready, so no traffic is being "
                "served. (simulated)"
            ),
            evidence=evidence,
        )

    def diagnose(self, failure: FailureEvent) -> Diagnosis:
        relevant = [item for item in failure.evidence if item.is_relevant]
        if relevant:
            return Diagnosis(
                likely_cause=(
                    "Readiness probe path does not match the application's health endpoint."
                ),
                explanation=(
                    "The application exposes /health, but the Deployment's readiness probe is "
                    "configured for /health/ready, which returns 404. Kubernetes never marks the "
                    "pod Ready, so the Service never sends it traffic."
                ),
                recommended_fix="Update the readiness probe path to /health and redeploy.",
                learning_moment=(
                    "Readiness vs liveness: a failing readiness probe removes a pod from Service "
                    "endpoints without restarting it, which is why the pod stays Running."
                ),
            )
        return Diagnosis(
            likely_cause="Unknown",
            explanation="No relevant evidence was found among the sources inspected.",
            recommended_fix="Inspect additional evidence sources before concluding.",
        )
