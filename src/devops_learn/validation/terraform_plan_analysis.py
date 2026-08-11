"""Pure risk analysis over a terraform ToolResult's plan details.

Kept separate from tools/terraform_tool.py (which only produces the raw plan
output) so the same risk rules could later run against a real `terraform
show -json` plan without touching the tool layer.
"""

from __future__ import annotations

from typing import Any, Mapping

from devops_learn.domain.enums import ChangeAction
from devops_learn.domain.plan_models import ResourceChange, TerraformPlanSummary
from devops_learn.tools.approval import RiskLevel


def analyze(details: Mapping[str, Any]) -> TerraformPlanSummary:
    create = int(details.get("create", 0))
    change = int(details.get("change", 0))
    replace = int(details.get("replace", 0))
    destroy = int(details.get("destroy", 0))

    changes = (
        tuple(ResourceChange(f"resource[{i}]", ChangeAction.CREATE) for i in range(create))
        + tuple(ResourceChange(f"resource[{i}]", ChangeAction.UPDATE) for i in range(change))
        + tuple(ResourceChange(f"resource[{i}]", ChangeAction.REPLACE) for i in range(replace))
        + tuple(ResourceChange(f"resource[{i}]", ChangeAction.DESTROY) for i in range(destroy))
    )

    if destroy > 0:
        return TerraformPlanSummary(
            changes=changes,
            risk_level=RiskLevel.DESTRUCTIVE,
            reason=f"{destroy} existing resource(s) will be destroyed.",
        )
    if replace > 0:
        return TerraformPlanSummary(
            changes=changes,
            risk_level=RiskLevel.HIGH,
            reason=f"{replace} existing resource(s) will be replaced (destroyed and recreated).",
        )
    if change > 0:
        return TerraformPlanSummary(
            changes=changes,
            risk_level=RiskLevel.LOW,
            reason=f"{change} existing resource(s) will be modified in place.",
        )
    return TerraformPlanSummary(
        changes=changes,
        risk_level=RiskLevel.SAFE,
        reason=f"{create} new resource(s) will be created; nothing existing is touched.",
    )
