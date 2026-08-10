from devops_learn.tools.approval import AutoApproveApprovalGate
from devops_learn.tools.service import ToolService
from devops_learn.tools.terraform_tool import SimulatedTerraformTool


def test_plan_derives_create_count_from_the_real_reference_config() -> None:
    """Proves the count comes from templates/terraform/main.tf.reference, not a
    hardcoded string: that file declares exactly 3 resource blocks."""
    service = ToolService({"terraform": SimulatedTerraformTool()}, AutoApproveApprovalGate())
    result = service.invoke("terraform", "plan")
    assert result.success is True
    assert result.details["create"] == 3
    assert result.details["destroy"] == 0


def test_destroy_requires_approval() -> None:
    from devops_learn.tools.approval import AutoDenyApprovalGate

    service = ToolService({"terraform": SimulatedTerraformTool()}, AutoDenyApprovalGate())
    result = service.invoke("terraform", "destroy_approved_environment")
    assert result.success is False
