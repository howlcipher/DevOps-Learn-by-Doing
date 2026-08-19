import sqlite3
from pathlib import Path
from typing import Any, Mapping

from devops_learn.bootstrap import build_platform
from devops_learn.domain.enums import AuditEventType
from devops_learn.tools.approval import AutoApproveApprovalGate
from devops_learn.tools.base import RiskLevel, Tool, ToolOperationSpec, ToolResult
from devops_learn.tools.docker_tool import SimulatedDockerTool
from devops_learn.tools.go_tool import SimulatedGoTool
from devops_learn.tools.python_tool import SimulatedPythonTool
from devops_learn.workflows.local_flow import LocalOptions, run_local_flow
from devops_learn.workflows.ui import Ui

REPO_ROOT = Path(__file__).resolve().parents[2]
GO_SERVICE = REPO_ROOT / "projects" / "go_service"
API_PLATFORM = REPO_ROOT / "projects" / "api_platform"


class DummyUi(Ui):
    def __init__(self) -> None:
        self.messages: list[str] = []

    def present(self, text: str) -> None:
        self.messages.append(text)

    def ask_choice(self, question: Any) -> str:
        return question.options[0] if question.options else ""

    def confirm(self, prompt: str, default: bool = True) -> bool:
        return default


def _make_platform(conn: sqlite3.Connection, custom_tools: dict[str, Tool] | None = None):
    tools = {
        "python": SimulatedPythonTool(),
        "go": SimulatedGoTool(),
        "docker": SimulatedDockerTool(),
    }
    if custom_tools:
        tools.update(custom_tools)
    return build_platform(
        conn,
        approval_gate=AutoApproveApprovalGate(),
        tools=tools,
    )


def test_local_flow_runs_successfully_for_go_service(conn: sqlite3.Connection, monkeypatch) -> None:
    platform = _make_platform(conn)
    ui = DummyUi()

    monkeypatch.setattr(
        "devops_learn.workflows.local_flow._verify_endpoint",
        lambda opts: "Health check OK (200): {\"status\": \"ok\"}",
    )

    options = LocalOptions(project_root=str(GO_SERVICE), host_port=8000)
    session = run_local_flow(platform, ui, options)

    assert session.id is not None
    events = platform.audit_service.history(session.id)
    event_summaries = [e.summary for e in events]

    assert "go.run_fmt_check" in event_summaries
    assert "go.run_vet" in event_summaries
    assert "go.run_tests" in event_summaries
    assert "go.run_build" in event_summaries
    assert "docker.build" in event_summaries
    assert "docker.run" in event_summaries
    assert "docker.logs" in event_summaries
    assert "docker.stop" in event_summaries
    assert "Local health check passed" in event_summaries

    experience = platform.experience_tracker.summary(session.id)
    assert "Go" in experience
    assert "Docker" in experience
    go_items = [entry.item for entry in experience["Go"]]
    assert "Ran format check (gofmt)" in go_items
    assert "Ran static analysis (go vet)" in go_items
    assert "Ran Go tests" in go_items
    assert "Compiled Go application" in go_items


def test_local_flow_runs_successfully_for_python_service(
    conn: sqlite3.Connection, monkeypatch
) -> None:
    platform = _make_platform(conn)
    ui = DummyUi()

    monkeypatch.setattr(
        "devops_learn.workflows.local_flow._verify_endpoint",
        lambda opts: "Health check OK (200): {\"status\": \"ok\"}",
    )

    options = LocalOptions(project_root=str(API_PLATFORM), host_port=8000)
    session = run_local_flow(platform, ui, options)

    assert session.id is not None
    events = platform.audit_service.history(session.id)
    event_summaries = [e.summary for e in events]

    assert "python.run_tests" in event_summaries
    assert "python.run_lint" in event_summaries
    assert "docker.build" in event_summaries
    assert "docker.run" in event_summaries
    assert "docker.stop" in event_summaries

    experience = platform.experience_tracker.summary(session.id)
    assert "Python" in experience
    assert "Docker" in experience


class FailingGoTool(Tool):
    def __init__(self, failing_op: str) -> None:
        self.failing_op = failing_op

    @property
    def name(self) -> str:
        return "go"

    @property
    def operations(self) -> tuple[ToolOperationSpec, ...]:
        return (
            ToolOperationSpec("run_fmt_check", RiskLevel.SAFE, False, False, False),
            ToolOperationSpec("run_vet", RiskLevel.SAFE, False, False, False),
            ToolOperationSpec("run_tests", RiskLevel.SAFE, False, False, False),
            ToolOperationSpec("run_build", RiskLevel.SAFE, False, False, False),
            ToolOperationSpec("verify_modules", RiskLevel.SAFE, False, False, False),
            ToolOperationSpec("version", RiskLevel.SAFE, False, False, False),
        )

    def execute(
        self, operation: str, params: Mapping[str, Any], *, dry_run: bool, approval: Any
    ) -> ToolResult:
        if operation == self.failing_op:
            return ToolResult(
                False, f"(simulated, failed) {operation} failed", {}, RiskLevel.SAFE, False
            )
        return ToolResult(True, f"(simulated) {operation} passed", {}, RiskLevel.SAFE, False)


def test_local_flow_fails_closed_on_go_format_failure(conn: sqlite3.Connection) -> None:
    platform = _make_platform(conn, {"go": FailingGoTool("run_fmt_check")})
    ui = DummyUi()

    options = LocalOptions(project_root=str(GO_SERVICE))
    session = run_local_flow(platform, ui, options)

    events = platform.audit_service.history(session.id)
    event_types = [e.event_type for e in events]
    event_summaries = [e.summary for e in events]

    assert AuditEventType.DEPLOYMENT_FAILED in event_types
    assert "docker.build" not in event_summaries
    assert "docker.run" not in event_summaries


def test_local_flow_fails_closed_on_go_vet_failure(conn: sqlite3.Connection) -> None:
    platform = _make_platform(conn, {"go": FailingGoTool("run_vet")})
    ui = DummyUi()

    options = LocalOptions(project_root=str(GO_SERVICE))
    session = run_local_flow(platform, ui, options)

    events = platform.audit_service.history(session.id)
    event_summaries = [e.summary for e in events]

    assert "Go vet failed" in event_summaries
    assert "docker.build" not in event_summaries


def test_local_flow_fails_closed_on_go_test_failure(conn: sqlite3.Connection) -> None:
    platform = _make_platform(conn, {"go": FailingGoTool("run_tests")})
    ui = DummyUi()

    options = LocalOptions(project_root=str(GO_SERVICE))
    session = run_local_flow(platform, ui, options)

    events = platform.audit_service.history(session.id)
    event_summaries = [e.summary for e in events]

    assert "Go tests failed" in event_summaries
    assert "docker.build" not in event_summaries


def test_local_flow_fails_closed_on_go_build_failure(conn: sqlite3.Connection) -> None:
    platform = _make_platform(conn, {"go": FailingGoTool("run_build")})
    ui = DummyUi()

    options = LocalOptions(project_root=str(GO_SERVICE))
    session = run_local_flow(platform, ui, options)

    events = platform.audit_service.history(session.id)
    event_summaries = [e.summary for e in events]

    assert "Go build failed" in event_summaries
    assert "docker.build" not in event_summaries


def test_local_flow_handles_health_check_failure(conn: sqlite3.Connection, monkeypatch) -> None:
    platform = _make_platform(conn)
    ui = DummyUi()

    monkeypatch.setattr(
        "devops_learn.workflows.local_flow._verify_endpoint",
        lambda opts: "Health check failed after 10 attempts at http://127.0.0.1:8000/health",
    )

    options = LocalOptions(project_root=str(GO_SERVICE))
    session = run_local_flow(platform, ui, options)

    events = platform.audit_service.history(session.id)
    event_types = [e.event_type for e in events]
    event_summaries = [e.summary for e in events]

    assert AuditEventType.DEPLOYMENT_FAILED in event_types
    assert "Local health check failed" in event_summaries
    experience = platform.experience_tracker.summary(session.id)
    assert "Troubleshooting" in experience
