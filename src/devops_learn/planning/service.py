"""PlanningService: turns an ArchitectureProposal into an ImplementationPlan of
concrete, controlled Tool operations (see tools/base.py).

Every PlanStep names a real (tools/*.py) operation, so the plan can be
executed directly by ToolService without a second translation layer, and a
human reviewing the plan is reviewing exactly what will run.
"""

from __future__ import annotations

from devops_learn.domain.architecture_models import ArchitectureProposal
from devops_learn.domain.enums import LanguageKind
from devops_learn.domain.plan_models import ImplementationPlan, PlanStep
from devops_learn.tools.approval import RiskLevel


class PlanningService:
    def build_plan(
        self,
        proposal: ArchitectureProposal,
        *,
        language: LanguageKind = LanguageKind.PYTHON,
    ) -> ImplementationPlan:
        if language is LanguageKind.GO:
            test_steps = [
                PlanStep(
                    id="tests",
                    title="Run the Go test suite",
                    tool_name="go",
                    operation="run_tests",
                    risk_level=RiskLevel.SAFE,
                    requires_approval=False,
                ),
                PlanStep(
                    id="vet",
                    title="Run static analysis (go vet)",
                    tool_name="go",
                    operation="run_vet",
                    risk_level=RiskLevel.SAFE,
                    requires_approval=False,
                ),
            ]
        else:
            test_steps = [
                PlanStep(
                    id="tests",
                    title="Run the test suite",
                    tool_name="python",
                    operation="run_tests",
                    risk_level=RiskLevel.SAFE,
                    requires_approval=False,
                ),
                PlanStep(
                    id="lint",
                    title="Run lint checks",
                    tool_name="python",
                    operation="run_lint",
                    risk_level=RiskLevel.SAFE,
                    requires_approval=False,
                ),
            ]

        steps = test_steps + [
            PlanStep(
                id="dockerfile_check",
                title="Validate Dockerfile best practices",
                tool_name="validation",
                operation="check_dockerfile_best_practices",
                risk_level=RiskLevel.SAFE,
                requires_approval=False,
            ),
            PlanStep(
                id="docker_build",
                title="Build the container image",
                tool_name="docker",
                operation="build",
                risk_level=RiskLevel.LOW,
                requires_approval=False,
            ),
            PlanStep(
                id="terraform_fmt",
                title="Format Terraform configuration",
                tool_name="terraform",
                operation="fmt",
                risk_level=RiskLevel.SAFE,
                requires_approval=False,
            ),
            PlanStep(
                id="terraform_validate",
                title="Validate Terraform configuration",
                tool_name="terraform",
                operation="validate",
                risk_level=RiskLevel.SAFE,
                requires_approval=False,
            ),
            PlanStep(
                id="terraform_plan",
                title="Produce a Terraform plan",
                tool_name="terraform",
                operation="plan",
                risk_level=RiskLevel.SAFE,
                requires_approval=False,
            ),
            PlanStep(
                id="terraform_apply",
                title="Apply the approved Terraform plan",
                tool_name="terraform",
                operation="apply_approved_plan",
                risk_level=RiskLevel.HIGH,
                requires_approval=True,
            ),
        ]
        if proposal.kubernetes_used:
            steps.append(
                PlanStep(
                    id="kubernetes_rollout",
                    title="Check Kubernetes rollout status",
                    tool_name="kubernetes",
                    operation="rollout_status",
                    risk_level=RiskLevel.SAFE,
                    requires_approval=False,
                )
            )
            steps.append(
                PlanStep(
                    id="kubernetes_pods",
                    title="Check pod health",
                    tool_name="kubernetes",
                    operation="get_pods",
                    risk_level=RiskLevel.SAFE,
                    requires_approval=False,
                )
            )
        else:
            steps.append(
                PlanStep(
                    id="docker_run",
                    title="Run the container",
                    tool_name="docker",
                    operation="run",
                    risk_level=RiskLevel.LOW,
                    requires_approval=False,
                )
            )
        steps.append(
            PlanStep(
                id="cloud_resources",
                title="List provisioned cloud resources",
                tool_name="cloud",
                operation="list_resources",
                risk_level=RiskLevel.SAFE,
                requires_approval=False,
            )
        )
        return ImplementationPlan(steps=tuple(steps))
