from typing import Any, Mapping

import pytest

from devops_learn.tools.approval import (
    ApprovalRecord,
    AutoApproveApprovalGate,
    AutoDenyApprovalGate,
)
from devops_learn.tools.base import RiskLevel, Tool, ToolOperationSpec, ToolResult
from devops_learn.tools.service import ToolService, UnknownToolError


class _SpyTool(Tool):
    """Wraps a real simulated tool, recording every execute() call it receives."""

    def __init__(self, wrapped: Tool) -> None:
        self._wrapped = wrapped
        self.execute_calls: list[tuple[str, dict[str, Any]]] = []

    @property
    def name(self) -> str:
        return self._wrapped.name

    @property
    def operations(self) -> tuple[ToolOperationSpec, ...]:
        return self._wrapped.operations

    def execute(
        self,
        operation: str,
        params: Mapping[str, Any],
        *,
        dry_run: bool,
        approval: ApprovalRecord | None,
    ) -> ToolResult:
        self.execute_calls.append((operation, dict(params)))
        return self._wrapped.execute(operation, params, dry_run=dry_run, approval=approval)


def test_destructive_operation_never_calls_execute_when_denied() -> None:
    from devops_learn.tools.cloud_tool import SimulatedCloudTool

    spy = _SpyTool(SimulatedCloudTool())
    service = ToolService({"cloud": spy}, AutoDenyApprovalGate())

    result = service.invoke("cloud", "delete_resource_group", {"resource_group": "prod-rg"})

    assert result.success is False
    assert result.approval is not None
    assert result.approval.granted is False
    assert spy.execute_calls == []


def test_destructive_operation_calls_execute_when_approved() -> None:
    from devops_learn.tools.cloud_tool import SimulatedCloudTool

    spy = _SpyTool(SimulatedCloudTool())
    service = ToolService({"cloud": spy}, AutoApproveApprovalGate())

    result = service.invoke("cloud", "delete_resource_group", {"resource_group": "prod-rg"})

    assert result.success is True
    assert spy.execute_calls == [("delete_resource_group", {"resource_group": "prod-rg"})]
    assert result.approval is not None and result.approval.granted is True


def test_safe_operation_never_prompts_for_approval() -> None:
    from devops_learn.tools.cloud_tool import SimulatedCloudTool

    spy = _SpyTool(SimulatedCloudTool())
    service = ToolService({"cloud": spy}, AutoDenyApprovalGate())

    result = service.invoke("cloud", "list_resources")

    assert result.success is True
    assert result.approval is None
    assert spy.execute_calls == [("list_resources", {})]


def test_unknown_tool_raises() -> None:
    service = ToolService({}, AutoApproveApprovalGate())
    with pytest.raises(UnknownToolError):
        service.invoke("nonexistent", "op")


def test_unknown_operation_raises() -> None:
    from devops_learn.tools.python_tool import SimulatedPythonTool

    service = ToolService({"python": SimulatedPythonTool()}, AutoApproveApprovalGate())
    with pytest.raises(KeyError):
        service.invoke("python", "does_not_exist")


def test_destructive_risk_without_approval_is_rejected_at_construction() -> None:
    with pytest.raises(ValueError):
        ToolOperationSpec(
            name="bad",
            risk_level=RiskLevel.DESTRUCTIVE,
            supports_dry_run=False,
            requires_approval=False,
            is_destructive=True,
        )


def test_dry_run_skips_approval_for_a_high_but_not_destructive_operation() -> None:
    from devops_learn.tools.docker_tool import SimulatedDockerTool

    spy = _SpyTool(SimulatedDockerTool())
    service = ToolService({"docker": spy}, AutoDenyApprovalGate())

    result = service.invoke("docker", "remove_image", dry_run=True)

    assert result.success is True
    assert result.was_dry_run is True
    assert spy.execute_calls == [("remove_image", {})]


def test_destructive_operations_can_never_declare_dry_run_support() -> None:
    with pytest.raises(ValueError):
        ToolOperationSpec(
            name="bad",
            risk_level=RiskLevel.DESTRUCTIVE,
            supports_dry_run=True,
            requires_approval=True,
            is_destructive=True,
        )


def test_dry_run_is_rejected_for_operations_that_do_not_support_it() -> None:
    from devops_learn.tools.cloud_tool import SimulatedCloudTool

    service = ToolService({"cloud": SimulatedCloudTool()}, AutoApproveApprovalGate())
    with pytest.raises(ValueError):
        service.invoke("cloud", "delete_resource_group", dry_run=True)
