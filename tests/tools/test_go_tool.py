from pathlib import Path

from devops_learn.tools._subprocess_safety import SafeRunResult
from devops_learn.tools.approval import AutoApproveApprovalGate
from devops_learn.tools.base import RiskLevel
from devops_learn.tools.go_tool import RealGoTool, SimulatedGoTool
from devops_learn.tools.service import ToolService

REPO_ROOT = Path(__file__).resolve().parents[2]
GO_SERVICE = REPO_ROOT / "projects" / "go_service"


def test_simulated_go_tool_operations() -> None:
    tool = SimulatedGoTool()
    assert tool.name == "go"
    for spec in tool.operations:
        assert spec.risk_level is RiskLevel.SAFE
        assert not spec.requires_approval
        assert not spec.is_destructive

    for op in ("run_tests", "run_vet", "run_build", "run_fmt_check", "verify_modules", "version"):
        res = tool.execute(op, {}, dry_run=False, approval=None)
        assert res.success
        assert "simulated" in res.summary


def test_simulated_go_tool_dry_run() -> None:
    tool = SimulatedGoTool()
    res = tool.execute("run_tests", {"path": "/some/path"}, dry_run=True, approval=None)
    assert res.success
    assert res.was_dry_run
    assert "dry run" in res.summary


def test_simulated_go_tool_through_tool_service() -> None:
    service = ToolService({"go": SimulatedGoTool()}, AutoApproveApprovalGate())
    result = service.invoke("go", "run_tests")
    assert result.success is True
    assert result.approval is None
    assert "passed" in result.summary


def test_real_go_tool_has_safe_operations() -> None:
    tool = RealGoTool()
    assert tool.name == "go"
    for spec in tool.operations:
        assert spec.risk_level is RiskLevel.SAFE
        assert not spec.requires_approval
        assert not spec.is_destructive


def test_real_go_tool_executes_on_bundled_go_service() -> None:
    tool = RealGoTool()
    path = str(GO_SERVICE)

    # 1. Format check
    fmt_res = tool.execute("run_fmt_check", {"path": path}, dry_run=False, approval=None)
    assert fmt_res.success
    assert "(real)" in fmt_res.summary

    # 2. Vet
    vet_res = tool.execute("run_vet", {"path": path}, dry_run=False, approval=None)
    assert vet_res.success
    assert "(real)" in vet_res.summary

    # 3. Test
    test_res = tool.execute("run_tests", {"path": path}, dry_run=False, approval=None)
    assert test_res.success
    assert "(real)" in test_res.summary

    # 4. Build
    build_res = tool.execute("run_build", {"path": path}, dry_run=False, approval=None)
    assert build_res.success
    assert "(real)" in build_res.summary

    # 5. Version
    ver_res = tool.execute("version", {"path": path}, dry_run=False, approval=None)
    assert ver_res.success
    assert "(real)" in ver_res.summary
    assert "go version" in ver_res.summary


def test_real_go_tool_dry_run() -> None:
    tool = RealGoTool()
    res = tool.execute("run_build", {"path": str(GO_SERVICE)}, dry_run=True, approval=None)
    assert res.success
    assert res.was_dry_run
    assert "dry run" in res.summary


def test_real_go_tool_reports_failure_on_bad_path() -> None:
    tool = RealGoTool()
    res = tool.execute("run_tests", {"path": "/nonexistent/go/path"}, dry_run=False, approval=None)
    assert not res.success
    assert "(real, failed)" in res.summary


def test_real_go_tool_handles_missing_binary(monkeypatch) -> None:
    import devops_learn.tools.go_tool as go_module
    monkeypatch.setattr(go_module.shutil, "which", lambda cmd: None)

    tool = RealGoTool()
    res = tool.execute("run_tests", {"path": str(GO_SERVICE)}, dry_run=False, approval=None)
    assert not res.success
    assert "(real, failed)" in res.summary
    assert "not found in PATH" in res.summary


def test_real_go_tool_handles_timeout(monkeypatch) -> None:
    import devops_learn.tools.go_tool as go_module

    def mock_run_safely(cmd, *, cwd, timeout):
        return SafeRunResult(returncode=-1, stdout="", stderr="timed out", timed_out=True)

    monkeypatch.setattr(go_module._subprocess_safety, "run_safely", mock_run_safely)

    tool = RealGoTool()
    res = tool.execute(
        "run_tests",
        {"path": str(GO_SERVICE), "timeout": 5},
        dry_run=False,
        approval=None,
    )
    assert not res.success
    assert "(real, failed)" in res.summary
    assert "timed out" in res.summary
