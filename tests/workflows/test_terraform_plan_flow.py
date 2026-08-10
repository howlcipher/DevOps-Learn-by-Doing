from devops_learn.tools.approval import AutoApproveApprovalGate
from devops_learn.tools.service import ToolService
from devops_learn.tools.terraform_tool import SimulatedTerraformTool
from devops_learn.workflows.terraform_plan_flow import validate_and_plan


def test_validate_and_plan_returns_both_results_in_order() -> None:
    tool_service = ToolService(
        {"terraform": SimulatedTerraformTool()}, AutoApproveApprovalGate()
    )
    result = validate_and_plan(tool_service)
    assert result.validate.success is True
    assert result.plan.success is True
    assert result.plan.details["create"] == 3
