from devops_learn.architecture.service import ArchitectureService
from devops_learn.cloud.azure.provider import AzureProvider
from devops_learn.planning.service import PlanningService
from devops_learn.tools.approval import RiskLevel


def test_plan_includes_a_high_risk_approval_gated_apply_step() -> None:
    proposal = ArchitectureService(AzureProvider()).propose(())
    plan = PlanningService().build_plan(proposal)
    apply_step = next(s for s in plan.steps if s.operation == "apply_approved_plan")
    assert apply_step.risk_level is RiskLevel.HIGH
    assert apply_step.requires_approval is True


def test_plan_uses_docker_run_when_kubernetes_is_not_used() -> None:
    proposal = ArchitectureService(AzureProvider()).propose(())
    plan = PlanningService().build_plan(proposal)
    operations = {(s.tool_name, s.operation) for s in plan.steps}
    assert ("docker", "run") in operations
    assert ("kubernetes", "rollout_status") not in operations
