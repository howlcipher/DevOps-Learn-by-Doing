from devops_learn.tools.approval import AutoApproveApprovalGate, AutoDenyApprovalGate
from devops_learn.tools.cloud_tool import SimulatedCloudTool
from devops_learn.tools.service import ToolService


def test_remove_identity_requires_approval() -> None:
    service = ToolService({"cloud": SimulatedCloudTool()}, AutoDenyApprovalGate())
    result = service.invoke("cloud", "remove_identity", {"identity": "workload-identity"})
    assert result.success is False


def test_estimate_cost_never_invents_a_precise_number() -> None:
    service = ToolService({"cloud": SimulatedCloudTool()}, AutoApproveApprovalGate())
    result = service.invoke("cloud", "estimate_cost")
    assert "$" not in result.summary
