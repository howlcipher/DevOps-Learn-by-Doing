"""Container OOM Termination troubleshooting scenario."""

from __future__ import annotations

import re
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


def _parse_memory_mb(mem_str: str) -> int:
    match = re.match(r"^(\d+)\s*([mMgGkK]?)[bB]?$", mem_str.strip())
    if not match:
        return 0
    val, unit = int(match.group(1)), match.group(2).upper()
    if unit == "G":
        return val * 1024
    if unit == "K":
        return max(1, val // 1024)
    return val  # defaults to MB


class ResourceLimitScenarioHandler(ScenarioHandler):
    @property
    def definition(self) -> TroubleshootingScenario:
        return TroubleshootingScenario(
            scenario_id="resource_limit",
            title="Container OOM Termination (Exit Code 137)",
            learning_objective=(
                "Recognize Out-Of-Memory (OOM) container termination (exit code 137, killed by "
                "kernel/cgroups without application traceback), inspect resource constraints, "
                "and allocate appropriate memory limits."
            ),
            category=CompetencyArea.DOCKER,
            fault_description=(
                "The container is configured with an insufficient 6MB memory limit where the "
                "runtime requires >20MB, triggering SIGKILL (exit code 137 / OOMKilled) on launch."
            ),
            expected_symptoms=(
                "Container terminates abruptly with exit code 137",
                "Application logs contain no Python traceback (abrupt kernel SIGKILL)",
                "Container state reports OOMKilled=true with memory limit 6m",
            ),
            allowed_diagnostic_tools=("docker.logs", "docker.run", "http_probe"),
            hints={
                0: (
                    "Observation: Container terminated with exit code 137 (SIGKILL). "
                    "Inspection state reports OOMKilled: true, MemoryLimit: 6m. "
                    "Application logs are abruptly truncated."
                ),
                1: (
                    "Inspection: Check the container exit code (137 = 128 + 9 / SIGKILL) "
                    "and inspect container memory limit configurations."
                ),
                2: (
                    "Subsystem: Container resource constraints & cgroup memory limits. "
                    "When memory exceeds the limit, the kernel OOM killer terminates the process."
                ),
                3: (
                    "Root Cause: The container memory limit of 6m is below the minimal runtime "
                    "requirement (~25MB), causing the Linux kernel to send SIGKILL."
                ),
                4: (
                    "Remediation: Increase the container memory limit: provide "
                    "{'memory_limit': '64m'} (or '64m' / '128m')."
                ),
            },
            success_criteria=(
                "Memory limit is increased to at least 32MB (e.g. '64m'), container starts and "
                "stays running (exit code 0), and passes /health probe."
            ),
            cleanup_requirements="Stop temporary test containers.",
        )

    def setup_and_inject(self, context: ScenarioContext) -> tuple[Observation, ...]:
        container_name = f"api-troubleshoot-oom-{id(context)}"
        context.state["container_name"] = container_name
        port = 8000
        context.state["port"] = port
        context.state["memory_limit"] = "6m"

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
                    exit_code=137,
                    is_error=True,
                    details={"exit_code": 137, "oom_killed": True, "memory_limit": "6m"},
                ),
                Observation(
                    source="docker.logs",
                    content=logs_res.summary or "<no application traceback: terminated by SIGKILL>",
                    exit_code=137,
                    is_error=True,
                ),
            )

        # Simulation mode deterministic observations
        obs1 = Observation(
            source="docker.run",
            content=(
                f"Container {container_name} terminated with exit code 137 "
                "(OOMKilled: true, memory_limit: 6m) (simulated)"
            ),
            exit_code=137,
            is_error=True,
            details={"exit_code": 137, "oom_killed": True, "memory_limit": "6m"},
        )
        obs2 = Observation(
            source="docker.logs",
            content=(
                "<process terminated abruptly by Linux OOM killer; no Python exception trace> "
                "(simulated)"
            ),
            exit_code=137,
            is_error=True,
        )
        obs3 = Observation(
            source="http_probe",
            content=(
                f"Health probe to http://127.0.0.1:{port}/health failed: "
                "connection refused (process terminated) (simulated)"
            ),
            is_error=True,
        )
        return (obs1, obs2, obs3)

    def remediate(
        self, context: ScenarioContext, attempt: RemediationAttempt
    ) -> tuple[Observation, ...]:
        limit_val: Any = attempt.parameters.get(
            "memory_limit", attempt.parameters.get("memory", attempt.parameters.get("limit"))
        )
        if limit_val is None:
            for part in attempt.action.replace("=", " ").split():
                if any(c.isdigit() for c in part) and any(
                    unit in part.lower() for unit in ("m", "g", "mb", "gb")
                ):
                    limit_val = part
                    break

        mem_mb = _parse_memory_mb(str(limit_val or ""))
        context.state["memory_mb"] = mem_mb
        context.state["memory_limit"] = str(limit_val or "")

        if mem_mb < 32:
            return (
                Observation(
                    source="remediation",
                    content=(
                        f"Failed remediation: Memory limit '{limit_val}' ({mem_mb}MB) is "
                        "insufficient. Python/FastAPI requires at least 32MB."
                    ),
                    is_error=True,
                ),
            )

        if context.is_live:
            c_name = context.state.get("container_name", f"api-troubleshoot-oom-{id(context)}")
            context.tool_service.invoke("docker", "stop", {"container": c_name})
            port = context.state.get("port", 8000)
            run_res = context.tool_service.invoke(
                "docker",
                "run",
                {
                    "image": "api-platform:dev",
                    "name": c_name,
                    "ports": {str(port): "8000"},
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
                    f"Container started with memory limit {limit_val} ({mem_mb}MB) and "
                    "stays running (simulated)"
                ),
                exit_code=0,
                is_error=False,
                details={"memory_limit": limit_val, "memory_mb": mem_mb},
            ),
        )

    def verify(
        self, context: ScenarioContext, attempt: RemediationAttempt
    ) -> VerificationResult:
        mem_mb = context.state.get("memory_mb", 0)
        if mem_mb < 32:
            obs = Observation(
                source="verification",
                content=(
                    f"Verification failed: Container memory allocation ({mem_mb}MB) "
                    "is insufficient, leading to OOM termination."
                ),
                exit_code=137,
                is_error=True,
            )
            return VerificationResult(
                success=False,
                summary=f"Recovery failed: Memory limit ({mem_mb}MB) is below threshold (32MB).",
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
                        summary=f"OOM failure resolved. Running steadily within {mem_mb}MB limit.",
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
                    summary=f"Verification failed: Container failed to respond at {url}",
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
            summary=(
                f"OOM failure resolved. Container running steadily within {mem_mb}MB limit "
                "(simulated)."
            ),
            observations=(obs,),
            is_live=False,
            details={"memory_mb": mem_mb, "status_code": 200},
        )

    def cleanup(self, context: ScenarioContext) -> None:
        container_name = context.state.get("container_name")
        if container_name:
            context.tool_service.invoke("docker", "stop", {"container": container_name})
