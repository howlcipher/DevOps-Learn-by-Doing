from pathlib import Path

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
