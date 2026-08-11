"""Local vertical slice: inspect -> test -> Dockerize -> build -> run -> verify.

This workflow runs real Python tests/lint and real Docker commands against a
project. It keeps simulated cloud/Terraform/Kubernetes tooling out of scope and
teaches concepts in context based on the learner profile.
"""

from __future__ import annotations

import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from devops_learn.bootstrap import Platform
from devops_learn.domain.enums import (
    AuditEventType,
    CloudProviderKind,
    CostPriority,
    EnvironmentKind,
    ExecutionMode,
    ExperienceState,
    ExplanationDepth,
)
from devops_learn.domain.explanation_models import Explanation
from devops_learn.domain.learner_profile_models import CompetencyArea
from devops_learn.domain.session_models import EngagementSession
from devops_learn.tools.base import ToolResult
from devops_learn.workflows import presenters
from devops_learn.workflows.ui import Ui


@dataclass(frozen=True)
class LocalOptions:
    project_root: str
    image_tag: str = "api-platform:dev"
    container_name: str = "api-platform-local"
    host_port: int = 8000
    inject_failure: bool = False


def run_local_flow(
    platform: Platform, ui: Ui, options: LocalOptions
) -> EngagementSession:
    session = platform.session_service.start(
        project_root=options.project_root,
        mode=ExecutionMode.COLLABORATIVE,
        explanation_depth=ExplanationDepth.LEARNING,
        cloud=CloudProviderKind.AZURE,
        environment=EnvironmentKind.DEV,
        cost_priority=CostPriority.BALANCED,
        simulation_mode=False,
    )
    assert session.id is not None
    session_id = session.id

    _audit(platform, session_id, AuditEventType.SESSION_STARTED, "Local workflow started")

    assessment = platform.analyzer.analyze(options.project_root)
    _audit(
        platform, session_id, AuditEventType.PROJECT_ANALYZED, f"Analyzed {options.project_root}"
    )
    ui.present(presenters.render_assessment(assessment))
    _teach_if_beginner(platform, ui, session_id, "docker", "Docker", _docker_intro())

    _run_python_step(
        platform, ui, session_id, "run_tests", {"path": options.project_root}, "Tests"
    )
    _run_python_step(
        platform,
        ui,
        session_id,
        "run_lint",
        {"path": options.project_root, "paths": ["."]},
        "Lint",
    )

    _teach_if_beginner(
        platform, ui, session_id, "docker", "Dockerfile", _dockerfile_intro()
    )

    build_result = _run_docker_step(
        platform,
        ui,
        session_id,
        "build",
        {
            "context": options.project_root,
            "tag": options.image_tag,
            "dockerfile": f"{options.project_root}/Dockerfile",
        },
        "Docker build",
    )
    if not build_result.success:
        _diagnose_and_cleanup(
            platform, ui, session_id, options, build_result, "Build failed"
        )
        platform.session_service.complete(session)
        return session

    run_result = _run_docker_step(
        platform,
        ui,
        session_id,
        "run",
        {
            "image": options.image_tag,
            "name": options.container_name,
            "ports": {str(options.host_port): "8000"},
        },
        "Docker run",
    )
    if not run_result.success:
        _diagnose_and_cleanup(
            platform, ui, session_id, options, run_result, "Run failed"
        )
        platform.session_service.complete(session)
        return session

    _teach_if_beginner(
        platform, ui, session_id, "docker", "Container verification", _verify_intro()
    )

    if options.inject_failure:
        _inject_failure(platform, ui, session_id, options)
    else:
        verify_result = _verify_endpoint(options)
        ui.present(verify_result)
        platform.audit_service.record(
            session_id=session_id,
            event_type=AuditEventType.DEPLOYMENT_SUCCEEDED,
            occurred_at=_now(),
            summary="Local health check passed",
        )
        platform.experience_tracker.record(
            session_id,
            "Docker",
            "Verified running container",
            ExperienceState.PRACTICED,
        )
        _show_logs(platform, ui, session_id, options)

    _stop_container(platform, ui, session_id, options)
    _print_history_and_experience(platform, ui, session_id)
    platform.session_service.complete(session)
    return session


def _audit(
    platform: Platform,
    session_id: int,
    event_type: AuditEventType,
    summary: str,
    payload: dict[str, Any] | None = None,
) -> None:
    platform.audit_service.record(
        session_id=session_id,
        event_type=event_type,
        occurred_at=_now(),
        summary=summary,
        payload=payload or {},
    )


def _run_python_step(
    platform: Platform,
    ui: Ui,
    session_id: int,
    operation: str,
    params: dict[str, Any],
    label: str,
) -> ToolResult:
    _explain(platform, ui, label, _python_explanation(label))
    result = platform.tool_service.invoke("python", operation, params)
    ui.present(result.summary)
    _audit(
        platform,
        session_id,
        AuditEventType.TOOL_INVOKED,
        f"python.{operation}",
        {"success": result.success},
    )
    platform.experience_tracker.record(
        session_id, "Python", f"Ran {operation}", ExperienceState.PRACTICED
    )
    return result


def _run_docker_step(
    platform: Platform,
    ui: Ui,
    session_id: int,
    operation: str,
    params: dict[str, Any],
    label: str,
) -> ToolResult:
    _explain(platform, ui, label, _docker_explanation(operation))
    result = platform.tool_service.invoke("docker", operation, params)
    ui.present(result.summary)
    _audit(
        platform,
        session_id,
        AuditEventType.TOOL_INVOKED,
        f"docker.{operation}",
        {"success": result.success},
    )
    return result


def _verify_endpoint(options: LocalOptions) -> str:
    url = f"http://127.0.0.1:{options.host_port}/health"
    attempts = 10
    for i in range(attempts):
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                body = response.read().decode("utf-8")
                return f"Health check OK ({response.status}): {body}"
        except urllib.error.URLError:
            if i == attempts - 1:
                return f"Health check failed after {attempts} attempts at {url}"
            time.sleep(1)
    return "Health check unreachable"


def _show_logs(
    platform: Platform, ui: Ui, session_id: int, options: LocalOptions
) -> None:
    result = platform.tool_service.invoke(
        "docker", "logs", {"container": options.container_name}
    )
    ui.present("Container logs:\n" + result.summary)
    _audit(
        platform,
        session_id,
        AuditEventType.TOOL_INVOKED,
        "docker.logs",
        {"success": result.success},
    )


def _stop_container(
    platform: Platform, ui: Ui, session_id: int, options: LocalOptions
) -> None:
    result = platform.tool_service.invoke(
        "docker", "stop", {"container": options.container_name}
    )
    ui.present(result.summary)
    _audit(
        platform,
        session_id,
        AuditEventType.TOOL_INVOKED,
        "docker.stop",
        {"success": result.success},
    )


def _diagnose_and_cleanup(
    platform: Platform,
    ui: Ui,
    session_id: int,
    options: LocalOptions,
    result: ToolResult,
    context: str,
) -> None:
    ui.present(f"{context}. Diagnosis starts from the output above.")
    _audit(platform, session_id, AuditEventType.DEPLOYMENT_FAILED, context)
    platform.experience_tracker.record(
        session_id,
        "Troubleshooting",
        f"Investigated {context}",
        ExperienceState.INTRODUCED,
    )
    _stop_container(platform, ui, session_id, options)


def _inject_failure(
    platform: Platform, ui: Ui, session_id: int, options: LocalOptions
) -> None:
    ui.present("Injecting a deliberate failure to practice troubleshooting.")
    broken_name = f"{options.container_name}-broken"
    broken_port = options.host_port + 1
    platform.tool_service.invoke(
        "docker",
        "run",
        {
            "image": options.image_tag,
            "name": broken_name,
            "ports": {str(broken_port): "8000"},
        },
    )
    verify = _verify_endpoint(
        LocalOptions(project_root=options.project_root, host_port=broken_port)
    )
    ui.present(verify)
    logs = platform.tool_service.invoke("docker", "logs", {"container": broken_name})
    ui.present("Broken container logs:\n" + logs.summary)
    _audit(
        platform,
        session_id,
        AuditEventType.TROUBLESHOOTING_STARTED,
        "Practiced troubleshooting a failing container",
    )
    ui.present(
        "DIAGNOSIS: The container exited or never served traffic. "
        "Container logs are the first place to look for a missing environment variable, "
        "bad command, or unhandled exception."
    )
    platform.tool_service.invoke("docker", "stop", {"container": broken_name})
    platform.experience_tracker.record(
        session_id,
        "Troubleshooting",
        "Diagnosed container failure from logs",
        ExperienceState.PRACTICED,
    )


def _teach_if_beginner(
    platform: Platform,
    ui: Ui,
    session_id: int,
    area_value: str,
    concept: str,
    text: str,
) -> None:
    profile = platform.learner_profile_service.load()
    if profile.is_strong(CompetencyArea(area_value)):
        return
    ui.present(f"LEARNING MOMENT: {concept}\n{text}")
    platform.experience_tracker.record(
        session_id, concept, "Concept explained", ExperienceState.INTRODUCED
    )


def _explain(
    platform: Platform, ui: Ui, label: str, explanation: Explanation
) -> None:
    rendered = platform.explanation_service.render(
        explanation,
        mode=ExecutionMode.COLLABORATIVE,
        depth=ExplanationDepth.LEARNING,
    )
    ui.present(rendered)


def _print_history_and_experience(
    platform: Platform, ui: Ui, session_id: int
) -> None:
    events = platform.audit_service.history(session_id)
    lines = ["AUDIT HISTORY", ""]
    for event in events:
        lines.append(f"{event.sequence_no:>3}. {event.event_type.value}: {event.summary}")
    ui.present("\n".join(lines))

    grouped = platform.experience_tracker.summary(session_id)
    lines = ["EXPERIENCE SUMMARY", ""]
    for concept, entries in grouped.items():
        lines.append(concept)
        for entry in entries:
            lines.append(f"  \u2713 {entry.item}")
        lines.append("")
    ui.present("\n".join(lines).rstrip())


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _python_explanation(label: str) -> Explanation:
    return Explanation(
        action=f"Running {label.lower()}.",
        why="Local tests and lint catch problems before they are packaged or deployed.",
    )


def _docker_explanation(operation: str) -> Explanation:
    if operation == "build":
        return Explanation(
            action="Building the container image.",
            why=(
                "A container image packages the application with its exact "
                "runtime dependencies."
            ),
            what_to_understand=(
                "Docker builds a layered image from a Dockerfile. Each instruction "
                "creates a layer; only changed layers are rebuilt, which is why "
                "order matters."
            ),
        )
    if operation == "run":
        return Explanation(
            action="Running the container locally.",
            why=(
                "Running the image proves it starts, binds to the expected port, "
                "and serves traffic."
            ),
            what_to_understand=(
                "A container is a running instance of an image. -p maps a host port "
                "to a container port so you can reach it from outside."
            ),
        )
    return Explanation(action=f"Running docker {operation}.")


def _docker_intro() -> str:
    return (
        "Docker packages an application and its dependencies into an image. "
        "A running image is called a container. Containers let the application run "
        "the same way on your laptop, in CI, and in the cloud."
    )


def _dockerfile_intro() -> str:
    return (
        "A Dockerfile is a recipe for building the image. It starts from a base "
        "image, copies source, installs dependencies, sets the command to run, and "
        "often uses a non-root user for security."
    )


def _verify_intro() -> str:
    return (
        "After starting a container, verify it actually works. A health endpoint "
        "like /health tells you the application is alive and able to respond to "
        "requests."
    )
