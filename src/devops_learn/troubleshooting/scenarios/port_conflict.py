"""Port Binding Collision troubleshooting scenario."""

from __future__ import annotations

import socket
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


class PortConflictScenarioHandler(ScenarioHandler):
    @property
    def definition(self) -> TroubleshootingScenario:
        return TroubleshootingScenario(
            scenario_id="port_conflict",
            title="Port Binding Collision (EADDRINUSE)",
            learning_objective=(
                "Diagnose socket bind failure when the host port is already occupied, "
                "distinguish host port collisions from container internal errors, and "
                "reconfigure port mappings to restore service reachability."
            ),
            category=CompetencyArea.NETWORKING,
            fault_description=(
                "Host port 8000 is occupied by another process/listener, causing "
                "the container to fail binding to 0.0.0.0:8000 on startup."
            ),
            expected_symptoms=(
                "Container startup fails with non-zero exit code (1)",
                (
                    "Error output contains 'bind: address already in use' or "
                    "'port is already allocated'"
                ),
                "HTTP probe to http://127.0.0.1:8000/health fails to reach target application",
            ),
            allowed_diagnostic_tools=("docker.logs", "docker.run", "http_probe", "socket_check"),
            hints={
                0: (
                    "Observation: Container failed startup on host port 8000. Stderr indicates "
                    "'bind: address already in use: 0.0.0.0:8000' (exit code 1)."
                ),
                1: (
                    "Inspection: Check container logs and host port allocation with "
                    "netstat/ss/lsof or Docker port bindings."
                ),
                2: (
                    "Subsystem: Network socket allocation. TCP ports are exclusive per network "
                    "interface; two processes cannot bind the same host port concurrently."
                ),
                3: (
                    "Root Cause: Host port 8000 is occupied by an existing listener process, "
                    "preventing the container from publishing to 0.0.0.0:8000."
                ),
                4: (
                    "Remediation: Map the container to an available host port (e.g. 8001 or 8080) "
                    "by setting 'port' or 'host_port' to an unused port number."
                ),
            },
            success_criteria=(
                "Application is mapped to an available host port (e.g. 8001), starts cleanly with "
                "exit code 0, and returns HTTP 200 on /health."
            ),
            cleanup_requirements="Release occupied port listeners and stop test containers.",
        )

    def setup_and_inject(self, context: ScenarioContext) -> tuple[Observation, ...]:
        container_name = f"api-troubleshoot-port-{id(context)}"
        context.state["container_name"] = container_name
        occupied_port = 8000
        context.state["occupied_port"] = occupied_port

        if context.is_live:
            # Bind an ephemeral local socket to simulate an occupied host port safely
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind(("127.0.0.1", occupied_port))
                sock.listen(1)
                context.state["conflicting_socket"] = sock
            except OSError as exc:
                context.state["socket_bind_error"] = str(exc)

            # Try to run container on occupied port
            run_res = context.tool_service.invoke(
                "docker",
                "run",
                {
                    "image": "api-platform:dev",
                    "name": container_name,
                    "ports": {str(occupied_port): "8000"},
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
                    exit_code=1 if not logs_res.success else 0,
                    is_error=not logs_res.success,
                    details=dict(logs_res.details),
                ),
                Observation(
                    source="http_probe",
                    content=f"Health probe to http://127.0.0.1:{occupied_port}/health failed",
                    is_error=True,
                ),
            )

        # Deterministic simulation mode
        obs1 = Observation(
            source="docker.run",
            content=(
                f"Error response from daemon: driver failed programming external connectivity on "
                f"endpoint {container_name}: Bind for 0.0.0.0:{occupied_port} failed: "
                "port is already allocated (simulated)"
            ),
            exit_code=1,
            is_error=True,
            details={"port": occupied_port, "error": "port_allocated"},
        )
        obs2 = Observation(
            source="docker.logs",
            content=(
                f"[ERROR] [uvicorn.error] Error while attempting to bind on address "
                f"('0.0.0.0', {occupied_port}): address already in use (simulated)"
            ),
            exit_code=1,
            is_error=True,
        )
        obs3 = Observation(
            source="http_probe",
            content=(
                f"Health check failed: connection refused or port collision at "
                f"http://127.0.0.1:{occupied_port}/health (simulated)"
            ),
            is_error=True,
        )
        return (obs1, obs2, obs3)

    def remediate(
        self, context: ScenarioContext, attempt: RemediationAttempt
    ) -> tuple[Observation, ...]:
        port_val: Any = attempt.parameters.get(
            "port", attempt.parameters.get("host_port", attempt.parameters.get("port_number"))
        )
        if port_val is None:
            for token in attempt.action.replace("=", " ").split():
                if token.isdigit() and int(token) > 0:
                    port_val = int(token)
                    break

        if port_val is not None:
            try:
                port_num = int(port_val)
            except ValueError:
                port_num = -1
        else:
            port_num = -1

        context.state["remediated_port"] = port_num
        occupied_port = context.state.get("occupied_port", 8000)

        if port_num == occupied_port or port_num <= 0 or port_num > 65535:
            return (
                Observation(
                    source="remediation",
                    content=(
                        f"Failed remediation: Port {port_num} is either invalid or still in "
                        f"conflict with occupied port {occupied_port}."
                    ),
                    is_error=True,
                ),
            )

        if context.is_live:
            container_name = context.state.get(
                "container_name", f"api-troubleshoot-port-{id(context)}"
            )
            context.tool_service.invoke("docker", "stop", {"container": container_name})
            run_res = context.tool_service.invoke(
                "docker",
                "run",
                {
                    "image": "api-platform:dev",
                    "name": container_name,
                    "ports": {str(port_num): "8000"},
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
                    f"Container started successfully, mapping host port {port_num} to "
                    "container port 8000 (simulated)"
                ),
                exit_code=0,
                is_error=False,
                details={"host_port": port_num, "container_port": 8000},
            ),
        )

    def verify(
        self, context: ScenarioContext, attempt: RemediationAttempt
    ) -> VerificationResult:
        port_num = context.state.get("remediated_port", -1)
        occupied_port = context.state.get("occupied_port", 8000)

        if port_num <= 0 or port_num == occupied_port or port_num > 65535:
            obs = Observation(
                source="verification",
                content=(
                    f"Verification failed: Port {port_num} is not a valid, non-conflicting port."
                ),
                is_error=True,
            )
            return VerificationResult(
                success=False,
                summary=f"Recovery failed: Service cannot bind to occupied port {port_num}.",
                observations=(obs,),
                is_live=context.is_live,
            )

        if context.is_live:
            url = f"http://127.0.0.1:{port_num}/health"
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
                        summary=f"Port collision resolved. Recovered on port {port_num}.",
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
                    summary=f"Verification failed: Unable to connect to {url}",
                    observations=(obs,),
                    is_live=True,
                )

        # Simulation mode deterministic verification
        obs = Observation(
            source="http_probe",
            content=(
                f"Health check OK (200): {{\"status\": \"ok\"}} at "
                f"http://127.0.0.1:{port_num}/health (simulated)"
            ),
            is_error=False,
        )
        return VerificationResult(
            success=True,
            summary=(
                f"Port collision resolved. Service recovered and verified on "
                f"host port {port_num} (simulated)."
            ),
            observations=(obs,),
            is_live=False,
            details={"port": port_num, "status_code": 200},
        )

    def cleanup(self, context: ScenarioContext) -> None:
        sock = context.state.get("conflicting_socket")
        if sock is not None:
            try:
                sock.close()
            except Exception:
                pass
            context.state["conflicting_socket"] = None

        container_name = context.state.get("container_name")
        if container_name:
            context.tool_service.invoke("docker", "stop", {"container": container_name})
