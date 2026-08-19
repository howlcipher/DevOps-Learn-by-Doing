"""Missing Required Configuration troubleshooting scenario."""

from __future__ import annotations

import urllib.error
import urllib.request
from typing import Any

from devops_learn.domain.learner_profile_models import CompetencyArea
from devops_learn.domain.troubleshooting_models import (
    Observation,
    RemediationAttempt,
    TroubleshootingScenario,
    VerificationResult,
)
from devops_learn.troubleshooting.scenarios.base import ScenarioContext, ScenarioHandler


class MissingConfigScenarioHandler(ScenarioHandler):
    @property
    def definition(self) -> TroubleshootingScenario:
        return TroubleshootingScenario(
            scenario_id="missing_config",
            title="Missing Required Configuration (Fail-Fast Startup)",
            learning_objective=(
                "Distinguish container process launch from application initialization crashes "
                "caused by missing mandatory environment variables, and supply correct "
                "configuration parameters."
            ),
            category=CompetencyArea.SECRETS,
            fault_description=(
                "The application requires mandatory environment setting 'REQUIRED_CONFIG_KEY' "
                "to initialize, but starts with an empty environment, causing a fail-fast crash."
            ),
            expected_symptoms=(
                "Container starts but exits immediately with exit code 1",
                "Stderr logs show 'ValueError: Mandatory environment variable "
                "'REQUIRED_CONFIG_KEY' is missing'",
                "HTTP health check fails due to container exit",
            ),
            allowed_diagnostic_tools=("docker.logs", "docker.run", "http_probe"),
            hints={
                0: (
                    "Observation: Application crashed during startup (exit code 1). Stderr: "
                    "'ValueError: Mandatory environment variable 'REQUIRED_CONFIG_KEY' is missing. "
                    "Application cannot initialize.'"
                ),
                1: (
                    "Inspection: Review the container startup logs to identify configuration "
                    "and initialization errors."
                ),
                2: (
                    "Subsystem: Application configuration & environment injection. 12-factor apps "
                    "fail fast during startup if required settings are undefined."
                ),
                3: (
                    "Root Cause: The application's configuration loader expects "
                    "'REQUIRED_CONFIG_KEY' to be present in os.environ."
                ),
                4: (
                    "Remediation: Supply the required configuration: provide "
                    "{'env': {'REQUIRED_CONFIG_KEY': 'dev_value'}} or specify "
                    "'REQUIRED_CONFIG_KEY=value'."
                ),
            },
            success_criteria=(
                "Application is provided with REQUIRED_CONFIG_KEY, starts cleanly with exit code "
                "0, and returns HTTP 200 on /health."
            ),
            cleanup_requirements="Stop temporary containers and clear environment overrides.",
        )

    def setup_and_inject(self, context: ScenarioContext) -> tuple[Observation, ...]:
        container_name = f"api-troubleshoot-config-{id(context)}"
        context.state["container_name"] = container_name
        port = 8000
        context.state["port"] = port

        if context.is_live:
            run_res = context.tool_service.invoke(
                "docker",
                "run",
                {
                    "image": "api-platform:dev",
                    "name": container_name,
                    "ports": {str(port): "8000"},
                },
            )
            logs_res = context.tool_service.invoke(
                "docker", "logs", {"container": container_name}
            )
            return (
                Observation(
                    source="docker.run",
                    content=run_res.summary,
                    exit_code=1 if not run_res.success else 0,
                    is_error=not run_res.success,
                    details=dict(run_res.details),
                ),
                Observation(
                    source="docker.logs",
                    content=logs_res.summary,
                    exit_code=1,
                    is_error=True,
                    details=dict(logs_res.details),
                ),
            )

        # Simulation mode deterministic observations
        obs1 = Observation(
            source="docker.run",
            content=f"Container {container_name} started and exited with code 1 (simulated)",
            exit_code=1,
            is_error=True,
        )
        obs2 = Observation(
            source="docker.logs",
            content=(
                "[CRITICAL] [app.config] Initialization error: "
                "ValueError: Mandatory environment variable 'REQUIRED_CONFIG_KEY' is missing. "
                "Application cannot initialize. (simulated)"
            ),
            exit_code=1,
            is_error=True,
            details={"error_type": "ValueError", "missing_variable": "REQUIRED_CONFIG_KEY"},
        )
        obs3 = Observation(
            source="http_probe",
            content=(
                f"Health probe to http://127.0.0.1:{port}/health failed: "
                "connection refused (simulated)"
            ),
            is_error=True,
        )
        return (obs1, obs2, obs3)

    def remediate(
        self, context: ScenarioContext, attempt: RemediationAttempt
    ) -> tuple[Observation, ...]:
        env_dict: dict[str, Any] = {}
        if isinstance(attempt.parameters.get("env"), dict):
            env_dict.update(attempt.parameters["env"])
        for k, v in attempt.parameters.items():
            if k in ("REQUIRED_CONFIG_KEY", "required_config_key", "config_key"):
                env_dict["REQUIRED_CONFIG_KEY"] = v

        if not env_dict and "=" in attempt.action:
            for part in attempt.action.split():
                if "=" in part:
                    k, v = part.split("=", 1)
                    if k.strip().upper() == "REQUIRED_CONFIG_KEY":
                        env_dict["REQUIRED_CONFIG_KEY"] = v.strip()

        context.state["supplied_env"] = env_dict

        key_val = env_dict.get("REQUIRED_CONFIG_KEY")
        if not key_val or not str(key_val).strip():
            return (
                Observation(
                    source="remediation",
                    content="Failed remediation: REQUIRED_CONFIG_KEY was not supplied.",
                    is_error=True,
                ),
            )

        if context.is_live:
            c_name = context.state.get(
                "container_name", f"api-troubleshoot-config-{id(context)}"
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
                    "env": env_dict,
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
                source="docker.run",
                content=(
                    f"Container restarted with REQUIRED_CONFIG_KEY='{key_val}' (simulated)"
                ),
                exit_code=0,
                is_error=False,
                details={"env": env_dict},
            ),
        )

    def verify(
        self, context: ScenarioContext, attempt: RemediationAttempt
    ) -> VerificationResult:
        env_dict = context.state.get("supplied_env", {})
        key_val = env_dict.get("REQUIRED_CONFIG_KEY")
        if not key_val or not str(key_val).strip():
            obs = Observation(
                source="verification",
                content="Verification failed: REQUIRED_CONFIG_KEY is missing from configuration.",
                is_error=True,
            )
            return VerificationResult(
                success=False,
                summary="Recovery failed: Application cannot start without REQUIRED_CONFIG_KEY.",
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
                        is_error=False,
                    )
                    return VerificationResult(
                        success=True,
                        summary="Missing configuration resolved. Application healthy.",
                        observations=(obs,),
                        is_live=True,
                    )
            except (urllib.error.URLError, OSError) as exc:
                obs = Observation(
                    source="http_probe",
                    content=f"Health probe to {url} failed: {exc}",
                    is_error=True,
                )
                return VerificationResult(
                    success=False,
                    summary=f"Verification failed: Probe unreachable at {url}",
                    observations=(obs,),
                    is_live=True,
                )

        obs = Observation(
            source="http_probe",
            content=(
                "Health check OK (200): {\"status\": \"ok\", \"config\": \"valid\"} (simulated)"
            ),
            is_error=False,
        )
        return VerificationResult(
            success=True,
            summary=(
                "Missing configuration resolved. "
                "Application initialized and healthy (simulated)."
            ),
            observations=(obs,),
            is_live=False,
            details={"status_code": 200, "config_verified": True},
        )

    def cleanup(self, context: ScenarioContext) -> None:
        container_name = context.state.get("container_name")
        if container_name:
            context.tool_service.invoke("docker", "stop", {"container": container_name})
