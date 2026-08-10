import pytest

from devops_learn.tools.approval import ApprovalRecord
from devops_learn.tools.base import ApprovalNotGrantedError
from devops_learn.tools.cloud_tool import SimulatedCloudTool
from devops_learn.tools.kubernetes_tool import SimulatedKubernetesTool

_APPROVAL_REQUIRING_TOOLS = (SimulatedCloudTool(), SimulatedKubernetesTool())


def _first_approval_requiring_operation(tool):
    return next(spec for spec in tool.operations if spec.requires_approval)


@pytest.mark.parametrize("tool", _APPROVAL_REQUIRING_TOOLS)
def test_execute_without_approval_raises(tool):
    spec = _first_approval_requiring_operation(tool)
    with pytest.raises(ApprovalNotGrantedError):
        tool.execute(spec.name, {}, dry_run=False, approval=None)


@pytest.mark.parametrize("tool", _APPROVAL_REQUIRING_TOOLS)
def test_execute_with_denied_approval_raises(tool):
    spec = _first_approval_requiring_operation(tool)
    denied = ApprovalRecord(granted=False, approved_by="test")
    with pytest.raises(ApprovalNotGrantedError):
        tool.execute(spec.name, {}, dry_run=False, approval=denied)
