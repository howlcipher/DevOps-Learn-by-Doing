"""TroubleshootingService: gathers structured evidence before ever asking for
a diagnosis, executes scenarios, provides progressive hints, and deterministically
verifies recovery.

Per the product spec, the AI is never handed a one-line failure description
and asked to guess: it always receives EvidenceItem / Observation entries gathered
from real (or, in simulation mode, simulated) ToolResult output first. See
docs/architecture.md#troubleshooting.
"""

from __future__ import annotations

from devops_learn.domain.troubleshooting_models import (
    Diagnosis,
    EvidenceItem,
    FailureEvent,
    HintLevel,
    Interpretation,
    Observation,
    RemediationAttempt,
    TroubleshootingEvidence,
    TroubleshootingScenario,
    TroubleshootingSession,
    VerificationResult,
)
from devops_learn.tools.service import ToolService
from devops_learn.troubleshooting.scenarios.base import ScenarioContext
from devops_learn.troubleshooting.scenarios.registry import ScenarioRegistry


class TroubleshootingService:
    def __init__(
        self,
        tool_service: ToolService,
        registry: ScenarioRegistry | None = None,
    ) -> None:
        self._tool_service = tool_service
        self._registry = registry or ScenarioRegistry()

    def list_scenarios(self) -> tuple[TroubleshootingScenario, ...]:
        return self._registry.list_scenarios()

    def get_scenario(self, scenario_id: str) -> TroubleshootingScenario:
        return self._registry.get_scenario(scenario_id)

    def start_session(
        self,
        scenario_id: str,
        *,
        project_root: str = ".",
        is_live: bool = False,
    ) -> tuple[TroubleshootingSession, ScenarioContext, tuple[Observation, ...]]:
        handler = self._registry.get_handler(scenario_id)
        scenario = handler.definition
        context = ScenarioContext(
            scenario=scenario,
            is_live=is_live,
            project_root=project_root,
            tool_service=self._tool_service,
        )
        initial_observations = handler.setup_and_inject(context)
        mode_label = "(real)" if is_live else "(simulated)"
        evidence = TroubleshootingEvidence(
            scenario_id=scenario_id,
            before_state=initial_observations,
            mode_label=mode_label,
        )
        session = TroubleshootingSession(
            scenario=scenario,
            is_live=is_live,
            project_root=project_root,
            evidence=evidence,
            active=True,
        )
        return session, context, initial_observations

    def get_hint(self, scenario_id: str, level: int | HintLevel) -> str:
        scenario = self.get_scenario(scenario_id)
        int_level = int(level)
        if int_level in scenario.hints:
            return scenario.hints[int_level]
        if int_level <= 0:
            return scenario.hints.get(0, "No evidence hint available.")
        max_level = max(scenario.hints.keys())
        return scenario.hints.get(max_level, "No further hints available.")

    def interpret(self, observations: tuple[Observation, ...]) -> tuple[Interpretation, ...]:
        interpretations: list[Interpretation] = []
        for obs in observations:
            if not obs.is_error:
                continue
            lower_content = obs.content.lower()
            if (
                "address already in use" in lower_content
                or "port is already allocated" in lower_content
            ):
                interpretations.append(
                    Interpretation(
                        observation_summary="Port bind conflict detected",
                        likely_subsystem="Networking / Socket Binding",
                        hypothesis="The requested host port is already bound by another process.",
                        confidence=0.95,
                    )
                )
            elif "required_config_key" in lower_content or (
                "missing" in lower_content and "config" in lower_content
            ):
                interpretations.append(
                    Interpretation(
                        observation_summary="Missing required configuration variable",
                        likely_subsystem="Application Configuration",
                        hypothesis=(
                            "Startup initialization failed because a required environment variable "
                            "was not supplied."
                        ),
                        confidence=0.95,
                    )
                )
            elif "503" in lower_content or "degraded" in lower_content:
                interpretations.append(
                    Interpretation(
                        observation_summary="Health probe returned HTTP 503 degraded",
                        likely_subsystem="Observability / Health Probes",
                        hypothesis=(
                            "Process is running but internal dependency check flagged "
                            "degraded readiness."
                        ),
                        confidence=0.90,
                    )
                )
            elif (
                "137" in str(obs.exit_code)
                or "oom" in lower_content
                or "sigkill" in lower_content
            ):
                interpretations.append(
                    Interpretation(
                        observation_summary="Process terminated by OOM killer (exit code 137)",
                        likely_subsystem="Resource Constraints / CGroups",
                        hypothesis=(
                            "Memory limit was exceeded during startup, causing kernel SIGKILL."
                        ),
                        confidence=0.95,
                    )
                )
        return tuple(interpretations)

    def remediate(
        self,
        session: TroubleshootingSession,
        context: ScenarioContext,
        attempt: RemediationAttempt,
    ) -> tuple[Observation, ...]:
        handler = self._registry.get_handler(session.scenario.scenario_id)
        return handler.remediate(context, attempt)

    def verify(
        self,
        session: TroubleshootingSession,
        context: ScenarioContext,
        attempt: RemediationAttempt,
    ) -> VerificationResult:
        handler = self._registry.get_handler(session.scenario.scenario_id)
        return handler.verify(context, attempt)

    def cleanup(
        self,
        session: TroubleshootingSession,
        context: ScenarioContext,
    ) -> None:
        handler = self._registry.get_handler(session.scenario.scenario_id)
        handler.cleanup(context)

    # -------------------------------------------------------------------------
    # Backward compatibility with V1 simulated Kubernetes failure
    # -------------------------------------------------------------------------

    def gather_evidence(self) -> FailureEvent:
        """Collects evidence for the intentional V1 simulated failure: a pod that
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
