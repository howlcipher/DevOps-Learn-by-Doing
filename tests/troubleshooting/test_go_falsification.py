"""Falsification tests: prove that real and simulated Go workflow failures
are reliably detected and fail closed rather than falsely reporting success.
"""

import sqlite3
from pathlib import Path

from devops_learn.analysis.project_analyzer import ProjectAnalyzer
from devops_learn.bootstrap import build_platform
from devops_learn.domain.enums import AuditEventType, LanguageKind
from devops_learn.tools.approval import AutoApproveApprovalGate
from devops_learn.tools.docker_tool import SimulatedDockerTool
from devops_learn.tools.go_tool import RealGoTool, SimulatedGoTool
from devops_learn.tools.python_tool import SimulatedPythonTool
from devops_learn.workflows.local_flow import LocalOptions, run_local_flow
from devops_learn.workflows.ui import Ui


class QuietUi(Ui):
    def __init__(self) -> None:
        self.messages: list[str] = []

    def present(self, text: str) -> None:
        self.messages.append(text)

    def ask_choice(self, question: object) -> str:
        return ""

    def confirm(self, prompt: str, default: bool = True) -> bool:
        return default


def test_falsification_1_real_go_unit_test_failure_is_detected(
    tmp_path: Path, conn: sqlite3.Connection
) -> None:
    # 1. Go unit test failure
    (tmp_path / "go.mod").write_text("module testfail\n\ngo 1.22\n")
    (tmp_path / "app.go").write_text("package main\n\nfunc Add(a, b int) int { return a + b }\n")
    (tmp_path / "app_test.go").write_text(
        "package main\n\n"
        "import \"testing\"\n\n"
        "func TestFailingCase(t *testing.T) {\n"
        "\tt.Fatalf(\"deliberate test failure\")\n"
        "}\n"
    )

    tool = RealGoTool()
    result = tool.execute("run_tests", {"path": str(tmp_path)}, dry_run=False, approval=None)
    assert not result.success
    assert "(real, failed)" in result.summary
    details_str = str(result.details.get("stdout", "")) + str(result.details.get("stderr", ""))
    assert "deliberate test failure" in details_str

    # Prove workflow fails closed on test failure
    platform = build_platform(
        conn,
        approval_gate=AutoApproveApprovalGate(),
        tools={"go": tool, "docker": SimulatedDockerTool(), "python": SimulatedPythonTool()},
    )
    session = run_local_flow(platform, QuietUi(), LocalOptions(project_root=str(tmp_path)))
    events = platform.audit_service.history(session.id)
    summaries = [e.summary for e in events]
    assert "docker.build" not in summaries
    assert "docker.run" not in summaries
    assert any(e.event_type == AuditEventType.DEPLOYMENT_FAILED for e in events)


def test_falsification_2_real_go_vet_failure_is_detected(
    tmp_path: Path, conn: sqlite3.Connection
) -> None:
    # 2. go vet failure (e.g. format string type mismatch)
    (tmp_path / "go.mod").write_text("module testvet\n\ngo 1.22\n")
    (tmp_path / "app.go").write_text(
        "package main\n\n"
        "import \"fmt\"\n\n"
        "func BadVet() {\n"
        "\tfmt.Printf(\"%d\", \"not a number\")\n"
        "}\n"
    )

    tool = RealGoTool()
    result = tool.execute("run_vet", {"path": str(tmp_path)}, dry_run=False, approval=None)
    assert not result.success
    assert "(real, failed)" in result.summary

    # Prove workflow fails closed on vet failure
    platform = build_platform(
        conn,
        approval_gate=AutoApproveApprovalGate(),
        tools={"go": tool, "docker": SimulatedDockerTool(), "python": SimulatedPythonTool()},
    )
    session = run_local_flow(platform, QuietUi(), LocalOptions(project_root=str(tmp_path)))
    events = platform.audit_service.history(session.id)
    summaries = [e.summary for e in events]
    assert "docker.build" not in summaries
    assert "docker.run" not in summaries


def test_falsification_3_real_go_compilation_failure_is_detected(tmp_path: Path) -> None:
    # 3. Go compilation failure
    (tmp_path / "go.mod").write_text("module testbuild\n\ngo 1.22\n")
    (tmp_path / "app.go").write_text(
        "package main\n\nfunc main() {\n\tinvalid syntax error here\n}\n"
    )

    tool = RealGoTool()
    result = tool.execute("run_build", {"path": str(tmp_path)}, dry_run=False, approval=None)
    assert not result.success
    assert "(real, failed)" in result.summary
    stderr = str(result.details.get("stderr", ""))
    assert "syntax error" in stderr or "expected" in stderr


def test_falsification_4_malformed_go_mod_is_detected(tmp_path: Path) -> None:
    # 4. malformed go.mod
    (tmp_path / "go.mod").write_text("this is completely invalid go.mod syntax @@##!!\n")

    tool = RealGoTool()
    result = tool.execute("run_build", {"path": str(tmp_path)}, dry_run=False, approval=None)
    assert not result.success
    assert "(real, failed)" in result.summary


def test_falsification_5_health_check_failure_is_detected(
    tmp_path: Path, conn: sqlite3.Connection, monkeypatch
) -> None:
    # 5. application builds but /health fails
    (tmp_path / "go.mod").write_text("module testhealth\n\ngo 1.22\n")
    (tmp_path / "app.go").write_text("package main\n\nfunc main() {}\n")

    platform = build_platform(
        conn,
        approval_gate=AutoApproveApprovalGate(),
        tools={
            "go": SimulatedGoTool(),
            "docker": SimulatedDockerTool(),
            "python": SimulatedPythonTool(),
        },
    )

    monkeypatch.setattr(
        "devops_learn.workflows.local_flow._verify_endpoint",
        lambda opts: "Health check failed after 10 attempts at http://127.0.0.1:8000/health",
    )

    session = run_local_flow(platform, QuietUi(), LocalOptions(project_root=str(tmp_path)))
    events = platform.audit_service.history(session.id)
    summaries = [e.summary for e in events]
    assert "Local health check failed" in summaries
    assert any(e.event_type == AuditEventType.DEPLOYMENT_FAILED for e in events)


def test_falsification_6_docker_container_exits_before_health_check(
    tmp_path: Path, conn: sqlite3.Connection, monkeypatch
) -> None:
    # 6. Docker container exits before health verification
    (tmp_path / "go.mod").write_text("module testexit\n\ngo 1.22\n")
    (tmp_path / "app.go").write_text("package main\n\nfunc main() {}\n")

    platform = build_platform(
        conn,
        approval_gate=AutoApproveApprovalGate(),
        tools={
            "go": SimulatedGoTool(),
            "docker": SimulatedDockerTool(),
            "python": SimulatedPythonTool(),
        },
    )

    monkeypatch.setattr(
        "devops_learn.workflows.local_flow._verify_endpoint",
        lambda opts: "Health check unreachable",
    )

    session = run_local_flow(platform, QuietUi(), LocalOptions(project_root=str(tmp_path)))
    events = platform.audit_service.history(session.id)
    assert any(e.event_type == AuditEventType.DEPLOYMENT_FAILED for e in events)


def test_falsification_7_unsupported_project_is_not_falsely_classified_as_go(
    tmp_path: Path,
) -> None:
    # 7. unsupported/non-Go project is not falsely classified as Go
    (tmp_path / "index.js").write_text("console.log('hello');\n")
    (tmp_path / "package.json").write_text('{"name": "js-app"}\n')

    assessment = ProjectAnalyzer().analyze(tmp_path)
    assert assessment.language is not LanguageKind.GO
    assert assessment.language is LanguageKind.UNKNOWN


def test_falsification_8_unformatted_go_project_fails_format_check(tmp_path: Path) -> None:
    # 8. Unformatted Go project is detected by gofmt check
    (tmp_path / "go.mod").write_text("module testfmt\n\ngo 1.22\n")
    (tmp_path / "app.go").write_text("package main\nfunc main(){\nvar x = 1\n_ = x}\n")

    tool = RealGoTool()
    result = tool.execute("run_fmt_check", {"path": str(tmp_path)}, dry_run=False, approval=None)
    assert not result.success
    assert "(real, failed)" in result.summary
    assert "Unformatted Go files found" in result.summary
