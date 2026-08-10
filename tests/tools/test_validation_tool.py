from devops_learn.tools.approval import AutoDenyApprovalGate
from devops_learn.tools.service import ToolService
from devops_learn.tools.validation_tool import SimulatedValidationTool


def test_check_dockerfile_best_practices_needs_no_approval() -> None:
    service = ToolService({"validation": SimulatedValidationTool()}, AutoDenyApprovalGate())
    result = service.invoke("validation", "check_dockerfile_best_practices")
    assert result.success is True
    assert result.approval is None
