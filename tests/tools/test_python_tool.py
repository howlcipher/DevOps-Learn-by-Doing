from devops_learn.tools.approval import AutoApproveApprovalGate
from devops_learn.tools.python_tool import SimulatedPythonTool
from devops_learn.tools.service import ToolService


def test_run_tests_is_safe_and_needs_no_approval() -> None:
    service = ToolService({"python": SimulatedPythonTool()}, AutoApproveApprovalGate())
    result = service.invoke("python", "run_tests")
    assert result.success is True
    assert result.approval is None
    assert "passed" in result.summary
