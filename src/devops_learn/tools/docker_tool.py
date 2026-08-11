"""DockerTool implementations: simulated for tests/no-Docker environments, and
real for local execution.

RealDockerTool shells out to the Docker CLI for a narrow allow-listed set of
operations. Every result clearly indicates REAL or SIMULATED.
"""

from __future__ import annotations

import shutil
import subprocess
from typing import Any, Mapping

from devops_learn.tools.approval import ApprovalRecord
from devops_learn.tools.base import RiskLevel, Tool, ToolOperationSpec, ToolResult

_OPERATIONS = (
    ToolOperationSpec(
        name="build",
        risk_level=RiskLevel.LOW,
        supports_dry_run=True,
        requires_approval=False,
        is_destructive=False,
    ),
    ToolOperationSpec(
        name="run",
        risk_level=RiskLevel.LOW,
        supports_dry_run=True,
        requires_approval=False,
        is_destructive=False,
    ),
    ToolOperationSpec(
        name="logs",
        risk_level=RiskLevel.SAFE,
        supports_dry_run=False,
        requires_approval=False,
        is_destructive=False,
    ),
    ToolOperationSpec(
        name="stop",
        risk_level=RiskLevel.LOW,
        supports_dry_run=False,
        requires_approval=False,
        is_destructive=False,
    ),
    ToolOperationSpec(
        name="remove_image",
        risk_level=RiskLevel.HIGH,
        supports_dry_run=True,
        requires_approval=True,
        is_destructive=True,
    ),
)


def _docker_command() -> str:
    command = shutil.which("docker")
    if command is None:
        raise FileNotFoundError(
            "Docker CLI not found. Install Docker or use simulation mode."
        )
    return command


def _run(command: list[str], *, check: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=check,
    )


class SimulatedDockerTool(Tool):
    @property
    def name(self) -> str:
        return "docker"

    @property
    def operations(self) -> tuple[ToolOperationSpec, ...]:
        return _OPERATIONS

    def execute(
        self,
        operation: str,
        params: Mapping[str, Any],
        *,
        dry_run: bool,
        approval: ApprovalRecord | None,
    ) -> ToolResult:
        spec = self.spec_for(operation)
        assert not spec.requires_approval or dry_run or (approval is not None and approval.granted)

        if operation == "build":
            summary = "Successfully built image api-platform:dev (simulated)"
            details: dict[str, Any] = {"image": "api-platform:dev", "layers": 6}
        elif operation == "run":
            summary = "Container started, listening on port 8000 (simulated)"
            details = {"container_id": "sim-container-01", "port": 8000}
        elif operation == "logs":
            summary = "INFO: Uvicorn running on http://0.0.0.0:8000 (simulated)"
            details = {"lines": 1}
        elif operation == "stop":
            name = params.get("container", "sim-container-01")
            summary = f"Stopped container {name} (simulated)"
            details = {"container": name}
        else:  # remove_image
            image = params.get("image", "api-platform:dev")
            summary = f"Removed image {image} (simulated)"
            details = {"image": image}

        return ToolResult(
            success=True,
            summary=summary,
            details=details,
            risk_level=spec.risk_level,
            was_dry_run=dry_run,
            approval=approval,
        )


class RealDockerTool(Tool):
    """Runs a small allow-list of Docker CLI commands locally."""

    @property
    def name(self) -> str:
        return "docker"

    @property
    def operations(self) -> tuple[ToolOperationSpec, ...]:
        return _OPERATIONS

    def execute(
        self,
        operation: str,
        params: Mapping[str, Any],
        *,
        dry_run: bool,
        approval: ApprovalRecord | None,
    ) -> ToolResult:
        spec = self.spec_for(operation)
        assert not spec.requires_approval or dry_run or (approval is not None and approval.granted)

        if dry_run:
            return ToolResult(
                success=True,
                summary=f"Would run docker {operation} with {dict(params)} (dry run)",
                details={"dry_run": True},
                risk_level=spec.risk_level,
                was_dry_run=dry_run,
                approval=approval,
            )

        try:
            docker = _docker_command()
            if operation == "build":
                context = params.get("context", ".")
                tag = params.get("tag", "api-platform:dev")
                file_arg = params.get("dockerfile", "Dockerfile")
                completed = _run(
                    [docker, "build", "-t", tag, "-f", file_arg, context]
                )
                success = completed.returncode == 0
                if completed.stdout:
                    summary = completed.stdout.strip().splitlines()[-1]
                else:
                    summary = "build complete"
                details = {
                    "returncode": completed.returncode,
                    "stderr": completed.stderr,
                }
            elif operation == "run":
                image = params.get("image", "api-platform:dev")
                name = params.get("name", "api-platform-local")
                ports = params.get("ports", {"8000": "8000"})
                port_args: list[str] = []
                for host_port, container_port in ports.items():
                    port_args.extend(["-p", f"{host_port}:{container_port}"])
                completed = _run(
                    [docker, "run", "-d", "--rm", "--name", name] + port_args + [image]
                )
                success = completed.returncode == 0
                summary = completed.stdout.strip() or f"container {name} started"
                details = {
                    "container": name,
                    "returncode": completed.returncode,
                    "stderr": completed.stderr,
                }
            elif operation == "logs":
                container = params.get("container", "api-platform-local")
                completed = _run([docker, "logs", container])
                success = completed.returncode == 0
                summary = completed.stdout.strip() or "no logs"
                details = {
                    "container": container,
                    "returncode": completed.returncode,
                    "stderr": completed.stderr,
                }
            elif operation == "stop":
                container = params.get("container", "api-platform-local")
                completed = _run([docker, "stop", container])
                success = completed.returncode == 0
                summary = f"Stopped container {container}"
                details = {
                    "container": container,
                    "returncode": completed.returncode,
                    "stderr": completed.stderr,
                }
            else:  # remove_image
                image = params.get("image", "api-platform:dev")
                completed = _run([docker, "rmi", image])
                success = completed.returncode == 0
                summary = f"Removed image {image}"
                details = {
                    "image": image,
                    "returncode": completed.returncode,
                    "stderr": completed.stderr,
                }
        except FileNotFoundError as exc:
            return ToolResult(
                success=False,
                summary=str(exc),
                details={},
                risk_level=spec.risk_level,
                was_dry_run=dry_run,
                approval=approval,
            )

        prefix = "(real) " if success else "(real, failed) "
        return ToolResult(
            success=success,
            summary=prefix + summary,
            details=details,
            risk_level=spec.risk_level,
            was_dry_run=dry_run,
            approval=approval,
        )
