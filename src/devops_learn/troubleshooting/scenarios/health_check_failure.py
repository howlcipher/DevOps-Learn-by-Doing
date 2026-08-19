"""Degraded Health Check troubleshooting scenario."""

from __future__ import annotations

import urllib.error
import urllib.request

from devops_learn.domain.learner_profile_models import CompetencyArea
from devops_learn.domain.troubleshooting_models import (
    Observation,
    RemediationAttempt,
    TroubleshootingScenario,
    VerificationResult,
)
from devops_learn.troubleshooting.scenarios.base import ScenarioContext, ScenarioHandler


class HealthCheckFailureScenarioHandler(ScenarioHandler):
    @property
    def definition(self) -> TroubleshootingScenario:
        return TroubleshootingScenario(
            scenario_id="health_check_failure",
            title="Degraded Health Check (Process Alive != Service Healthy)",
            learning_objective=(
                "Understand why a running container process can still fail readiness and health "
                "checks when internal dependencies report degraded state, inspect HTTP probe "
                "payload, and restore dependency health."
            ),
            category=CompetencyArea.OBSERVABILITY,
            fault_description=(
                "The application starts and container remains RUNNING, but internal dependency "
                "state is degraded, causing GET /health to return HTTP 503 Service Unavailable."
            ),
            expected_symptoms=(
                "Container is RUNNING with exit code 0",
                "Application logs show server listening normally",
                "HTTP GET /health returns HTTP 503 with JSON payload "
                "{'status': 'degraded', 'reason': 'database_dependency_unhealthy'}",
            ),
            allowed_diagnostic_tools=("docker.logs", "http_probe", "docker.run"),
            hints={
                0: (
                    "Observation: Container is RUNNING (exit code 0), but GET /health returned 503 "
                    "with payload '{\"status\": \"degraded\", \"reason\": "
                    "\"database_dependency_unhealthy\"}'."
                ),
                1: (
                    "Inspection: Query the /health endpoint directly and inspect the HTTP status "
                    "code and response JSON body."
                ),
                2: (
                    "Subsystem: Application health and readiness probe layer. A running process "
                    "does not mean the service is ready for traffic."
                ),
                3: (
                    "Root Cause: The internal dependency check flag is set to 'unhealthy'/"
                    "'degraded', returning 503."
                ),
                4: (
                    "Remediation: Resolve dependency health status by providing "
                    "{'dependency_status': 'healthy'} or 'dependency_status=healthy'."
                ),
            },
            success_criteria=(
                "Dependency state is set to 'healthy', and GET /health returns HTTP 200 with "
                "status 'ok'."
            ),
            cleanup_requirements="Stop temporary test containers and reset dependency state.",
        )

    def setup_and_inject(self, context: ScenarioContext) -> tuple[Observation, ...]:
        container_name = f"api-troubleshoot-health-{id(context)}"
        context.state["container_name"] = container_name
        port = 8000
        context.state["port"] = port
        context.state["dependency_status"] = "unhealthy"

        if context.is_live:
            run_res = context.tool_service.invoke(
                "docker",
                "run",
                {
                    "image": "api-platform:dev",
                    "name": container_name,
                    "ports": {str(port): "8000"},
                    "env": {"DEPENDENCY_STATUS": "unhealthy"},
                },
            )
            logs_res = context.tool_service.invoke(
                "docker", "logs", {"container": container_name}
            )
            return (
                Observation(
                    source="docker.run",
                    content=run_res.summary,
                    exit_code=0,
                    is_error=False,
                    details=dict(run_res.details),
                ),
                Observation(
                    source="docker.logs",
                    content=logs_res.summary or "INFO: Uvicorn running on http://0.0.0.0:8000",
                    exit_code=0,
                    is_error=False,
                ),
                Observation(
                    source="http_probe",
                    content=(
                        "HTTP 503 Service Unavailable: "
                        "{\"status\": \"degraded\", \"reason\": \"database_dependency_unhealthy\"}"
                    ),
                    exit_code=503,
                    is_error=True,
                ),
            )

        # Simulation mode deterministic observations
        obs1 = Observation(
            source="docker.run",
            content=f"Container {container_name} started and running (exit code 0) (simulated)",
            exit_code=0,
            is_error=False,
        )
        obs2 = Observation(
            source="docker.logs",
            content=(
                "INFO: [uvicorn.access] 127.0.0.1 - \"GET /health HTTP/1.1\" "
                "503 Service Unavailable (simulated)"
            ),
            exit_code=0,
            is_error=False,
        )
        obs3 = Observation(
            source="http_probe",
            content=(
                "HTTP 503 Service Unavailable: "
                "{\"status\": \"degraded\", \"reason\": \"database_dependency_unhealthy\"} "
                "(simulated)"
            ),
            exit_code=503,
            is_error=True,
            details={
                "status_code": 503,
                "body": {"status": "degraded", "reason": "database_dependency_unhealthy"},
            },
        )
        return (obs1, obs2, obs3)

    def remediate(
        self, context: ScenarioContext, attempt: RemediationAttempt
    ) -> tuple[Observation, ...]:
        status_val = attempt.parameters.get(
            "dependency_status",
            attempt.parameters.get("status", attempt.parameters.get("heal")),
        )
        if status_val is None:
            for part in attempt.action.replace("=", " ").split():
                if part.lower() in ("healthy", "ok", "true", "heal", "fix"):
                    status_val = "healthy"
                    break

        if str(status_val).lower() in ("healthy", "ok", "true", "heal"):
            context.state["dependency_status"] = "healthy"
        else:
            context.state["dependency_status"] = "unhealthy"

        if context.state["dependency_status"] != "healthy":
            return (
                Observation(
                    source="remediation",
                    content=(
                        f"Failed remediation: Dependency status was not resolved to 'healthy' "
                        f"(got '{status_val}')."
                    ),
                    is_error=True,
                ),
            )

        if context.is_live:
            c_name = context.state.get(
                "container_name", f"api-troubleshoot-health-{id(context)}"
            )
            context.tool_service.invoke("docker", "stop", {"container": c_name})
            port = context.state.get("port", 8000)
            run_res = context.tool_service.invoke(
                "docker",
                "run",
                {
                    "image": "api-platform:dev",
                    "name": c_name,
                    "ports": {str(port): "8000"},
                    "env": {"DEPENDENCY_STATUS": "healthy"},
                },
            )
            return (
                Observation(
                    source="docker.run",
                    content=run_res.summary,
                    exit_code=0 if run_res.success else 1,
                    is_error=not run_res.success,
                    details=dict(run_res.details),
                ),
            )

        return (
            Observation(
                source="remediation",
                content=(
                    "Dependency status updated to 'healthy'. "
                    "Application reloaded health state (simulated)."
                ),
                exit_code=0,
                is_error=False,
            ),
        )

    def verify(
        self, context: ScenarioContext, attempt: RemediationAttempt
    ) -> VerificationResult:
        if context.state.get("dependency_status") != "healthy":
            obs = Observation(
                source="http_probe",
                content=(
                    "HTTP 503 Service Unavailable: "
                    "{\"status\": \"degraded\", \"reason\": \"database_dependency_unhealthy\"}"
                ),
                exit_code=503,
                is_error=True,
            )
            return VerificationResult(
                success=False,
                summary=(
                    "Verification failed: /health is still returning HTTP 503 Service Unavailable."
                ),
                observations=(obs,),
                is_live=context.is_live,
            )

        if context.is_live:
            port = context.state.get("port", 8000)
            url = f"http://127.0.0.1:{port}/health"
            try:
                with urllib.request.urlopen(url, timeout=3) as resp:
                    body = resp.read().decode("utf-8")
                    obs = Observation(
                        source="http_probe",
                        content=f"Health check OK ({resp.status}): {body}",
                        exit_code=resp.status,
                        is_error=False,
                    )
                    return VerificationResult(
                        success=True,
                        summary="Health check failure resolved. /health returned HTTP 200 OK.",
                        observations=(obs,),
                        is_live=True,
                    )
            except (urllib.error.HTTPError, urllib.error.URLError, OSError) as exc:
                obs = Observation(
                    source="http_probe",
                    content=f"Health probe to {url} failed: {exc}",
                    is_error=True,
                )
                return VerificationResult(
                    success=False,
                    summary=f"Verification failed: Health probe to {url} failed",
                    observations=(obs,),
                    is_live=True,
                )

        obs = Observation(
            source="http_probe",
            content="Health check OK (200): {\"status\": \"ok\"} (simulated)",
            exit_code=200,
            is_error=False,
        )
        return VerificationResult(
            success=True,
            summary="Health check failure resolved. /health returned HTTP 200 OK (simulated).",
            observations=(obs,),
            is_live=False,
            details={"status_code": 200, "status": "ok"},
        )

    def cleanup(self, context: ScenarioContext) -> None:
        container_name = context.state.get("container_name")
        if container_name:
            context.tool_service.invoke("docker", "stop", {"container": container_name})
