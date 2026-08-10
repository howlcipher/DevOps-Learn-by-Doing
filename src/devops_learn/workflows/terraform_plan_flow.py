"""Runs the simulated Terraform validate/plan sequence for module_04_terraform_plan."""

from __future__ import annotations

from dataclasses import dataclass

from devops_learn.tools.base import ToolResult
from devops_learn.tools.service import ToolService


@dataclass(frozen=True)
class TerraformPlanResult:
    validate: ToolResult
    plan: ToolResult


def validate_and_plan(tool_service: ToolService) -> TerraformPlanResult:
    validate_result = tool_service.invoke("terraform", "validate")
    plan_result = tool_service.invoke("terraform", "plan")
    return TerraformPlanResult(validate=validate_result, plan=plan_result)
