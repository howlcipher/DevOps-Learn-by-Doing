"""Every declared operation of every simulated tool is reachable through ToolService.

Guards the safety boundary claim in docs/safety.md at the level of individual
operations: each one returns a simulated summary and never escalates its own
declared risk level.
"""

import pytest

from devops_learn.tools.approval import AutoApproveApprovalGate
from devops_learn.tools.base import Tool
from devops_learn.tools.cloud_tool import SimulatedCloudTool
from devops_learn.tools.docker_tool import SimulatedDockerTool
from devops_learn.tools.git_tool import SimulatedGitTool
from devops_learn.tools.kubernetes_tool import SimulatedKubernetesTool
from devops_learn.tools.python_tool import SimulatedPythonTool
from devops_learn.tools.service import ToolService
from devops_learn.tools.terraform_tool import SimulatedTerraformTool
from devops_learn.tools.validation_tool import SimulatedValidationTool

_TOOLS: tuple[Tool, ...] = (
    SimulatedPythonTool(),
    SimulatedGitTool(),
    SimulatedDockerTool(),
    SimulatedTerraformTool(),
    SimulatedKubernetesTool(),
    SimulatedCloudTool(),
    SimulatedValidationTool(),
)


@pytest.mark.parametrize(
    ("tool", "operation"),
    [(tool, spec.name) for tool in _TOOLS for spec in tool.operations],
    ids=[f"{tool.name}.{spec.name}" for tool in _TOOLS for spec in tool.operations],
)
def test_every_operation_returns_a_simulated_result(tool: Tool, operation: str) -> None:
    service = ToolService({tool.name: tool}, AutoApproveApprovalGate())

    result = service.invoke(tool.name, operation)

    assert result.success is True
    assert "simulat" in result.summary.lower()
    assert result.was_dry_run is False
    assert result.risk_level is tool.spec_for(operation).risk_level


@pytest.mark.parametrize(
    ("tool", "operation"),
    [(tool, spec.name) for tool in _TOOLS for spec in tool.operations if spec.supports_dry_run],
    ids=[
        f"{tool.name}.{spec.name}"
        for tool in _TOOLS
        for spec in tool.operations
        if spec.supports_dry_run
    ],
)
def test_dry_run_operations_report_themselves_as_dry_runs(tool: Tool, operation: str) -> None:
    service = ToolService({tool.name: tool}, AutoApproveApprovalGate())

    result = service.invoke(tool.name, operation, dry_run=True)

    assert result.was_dry_run is True
    assert result.approval is None


@pytest.mark.parametrize(
    ("tool", "operation", "params", "expected"),
    [
        (SimulatedGitTool(), "commit", {"message": "add dockerfile"}, "add dockerfile"),
        (SimulatedDockerTool(), "remove_image", {"image": "api-platform:v2"}, "api-platform:v2"),
        (SimulatedKubernetesTool(), "delete_namespace", {"namespace": "staging"}, "staging"),
        (SimulatedCloudTool(), "remove_identity", {"identity": "api-sp"}, "api-sp"),
        (SimulatedCloudTool(), "delete_resource_group", {"resource_group": "rg-test"}, "rg-test"),
    ],
    ids=["git.commit", "docker.remove_image", "k8s.delete_namespace", "cloud.remove_identity",
         "cloud.delete_resource_group"],
)
def test_parameterized_operations_echo_their_target(
    tool: Tool, operation: str, params: dict[str, str], expected: str
) -> None:
    service = ToolService({tool.name: tool}, AutoApproveApprovalGate())

    result = service.invoke(tool.name, operation, params)

    assert expected in result.summary
