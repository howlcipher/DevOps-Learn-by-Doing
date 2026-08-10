from devops_learn.tools.approval import AutoDenyApprovalGate
from devops_learn.tools.docker_tool import SimulatedDockerTool
from devops_learn.tools.service import ToolService


def test_remove_image_requires_approval_and_is_denied_by_default_gate() -> None:
    service = ToolService({"docker": SimulatedDockerTool()}, AutoDenyApprovalGate())
    result = service.invoke("docker", "remove_image", {"image": "api-platform:dev"})
    assert result.success is False


def test_build_does_not_require_approval() -> None:
    service = ToolService({"docker": SimulatedDockerTool()}, AutoDenyApprovalGate())
    result = service.invoke("docker", "build")
    assert result.success is True
