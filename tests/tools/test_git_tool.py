from devops_learn.tools.approval import AutoApproveApprovalGate
from devops_learn.tools.git_tool import SimulatedGitTool
from devops_learn.tools.service import ToolService


def test_commit_dry_run_does_not_claim_it_actually_committed() -> None:
    service = ToolService({"git": SimulatedGitTool()}, AutoApproveApprovalGate())
    result = service.invoke("git", "commit", {"message": "add dockerfile"}, dry_run=True)
    assert result.success is True
    assert "Would commit" in result.summary


def test_status_is_safe() -> None:
    service = ToolService({"git": SimulatedGitTool()}, AutoApproveApprovalGate())
    result = service.invoke("git", "status")
    assert result.approval is None
