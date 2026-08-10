from devops_learn.tools.approval import AutoApproveApprovalGate, AutoDenyApprovalGate
from devops_learn.tools.kubernetes_tool import SimulatedKubernetesTool
from devops_learn.tools.service import ToolService


def test_get_pods_needs_no_approval() -> None:
    service = ToolService({"k8s": SimulatedKubernetesTool()}, AutoDenyApprovalGate())
    result = service.invoke("k8s", "get_pods")
    assert result.success is True


def test_delete_namespace_requires_approval() -> None:
    service = ToolService({"k8s": SimulatedKubernetesTool()}, AutoDenyApprovalGate())
    result = service.invoke("k8s", "delete_namespace", {"namespace": "api-platform"})
    assert result.success is False


def test_rollback_succeeds_when_approved() -> None:
    service = ToolService({"k8s": SimulatedKubernetesTool()}, AutoApproveApprovalGate())
    result = service.invoke("k8s", "rollback")
    assert result.success is True
