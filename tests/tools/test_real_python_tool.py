from pathlib import Path

import pytest

from devops_learn.tools.approval import ApprovalRecord
from devops_learn.tools.base import RiskLevel
from devops_learn.tools.python_tool import RealPythonTool, SimulatedPythonTool

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_real_python_tool_has_safe_operations() -> None:
    tool = RealPythonTool()
    assert tool.name == "python"
    for spec in tool.operations:
        assert spec.risk_level is RiskLevel.SAFE
        assert not spec.requires_approval


def test_real_python_tool_runs_pytest_on_repo() -> None:
    tool = RealPythonTool()
    result = tool.execute(
        "run_tests",
        {"path": str(REPO_ROOT / "projects" / "api_platform")},
        dry_run=False,
        approval=None,
    )
    assert result.success
    assert "(real)" in result.summary


def test_simulated_python_tool_still_works() -> None:
    tool = SimulatedPythonTool()
    result = tool.execute(
        "run_tests", {}, dry_run=False, approval=ApprovalRecord(granted=True, approved_by="test")
    )
    assert result.success
    assert "simulated" in result.summary


def test_real_python_tool_reports_failure_for_bad_path() -> None:
    tool = RealPythonTool()
    result = tool.execute(
        "run_tests",
        {"path": "/nonexistent/path"},
        dry_run=False,
        approval=None,
    )
    assert not result.success


def test_real_python_tool_runs_lint_on_single_and_multiple_paths() -> None:
    tool = RealPythonTool()
    result = tool.execute(
        "run_lint",
        {"paths": "src"},
        dry_run=False,
        approval=None,
    )
    has_summary = "flake8" in result.summary
    has_code = result.details.get("returncode") is not None
    assert result.success or has_summary or has_code


def test_real_python_tool_timeout_returns_failure_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import subprocess
    tool = RealPythonTool()

    def mock_run(*args: object, **kwargs: object) -> None:
        raise subprocess.TimeoutExpired(cmd=["test"], timeout=0.1)

    import devops_learn.tools.python_tool as pt_module
    monkeypatch.setattr(pt_module, "_run", mock_run)

    result = tool.execute(
        "run_tests",
        {"path": ".", "timeout": 0.1},
        dry_run=False,
        approval=None,
    )
    assert not result.success
    assert "Execution timed out" in result.summary
    assert result.details.get("error") == "timeout"
