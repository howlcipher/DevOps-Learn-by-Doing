"""Simulated TerraformTool. No real terraform binary invoked in V1; see docs/safety.md.

plan() derives its resource count from templates/terraform/main.tf.reference
instead of a hardcoded string, so the learner's interpretation question stays
meaningful and the reference config can change without a second edit site.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Mapping

from devops_learn.tools.approval import ApprovalRecord
from devops_learn.tools.base import (
    RiskLevel,
    Tool,
    ToolOperationSpec,
    ToolResult,
    ensure_approved,
)

_OPERATIONS = (
    ToolOperationSpec(
        name="fmt",
        risk_level=RiskLevel.SAFE,
        supports_dry_run=False,
        requires_approval=False,
        is_destructive=False,
    ),
    ToolOperationSpec(
        name="validate",
        risk_level=RiskLevel.SAFE,
        supports_dry_run=False,
        requires_approval=False,
        is_destructive=False,
    ),
    ToolOperationSpec(
        name="plan",
        risk_level=RiskLevel.SAFE,
        supports_dry_run=False,
        requires_approval=False,
        is_destructive=False,
    ),
    ToolOperationSpec(
        name="apply_approved_plan",
        risk_level=RiskLevel.HIGH,
        supports_dry_run=False,
        requires_approval=True,
        is_destructive=False,
    ),
    ToolOperationSpec(
        name="destroy_approved_environment",
        risk_level=RiskLevel.DESTRUCTIVE,
        supports_dry_run=False,
        requires_approval=True,
        is_destructive=True,
    ),
)

_RESOURCE_BLOCK_PATTERN = re.compile(r'^\s*resource\s+"', re.MULTILINE)
_FALLBACK_RESOURCE_COUNT = 3


def _reference_config_path() -> Path:
    # src/devops_learn/tools/terraform_tool.py -> repo root is 3 parents up.
    return Path(__file__).resolve().parents[3] / "templates" / "terraform" / "main.tf.reference"


def _count_declared_resources() -> int:
    path = _reference_config_path()
    if not path.is_file():
        return _FALLBACK_RESOURCE_COUNT
    return len(_RESOURCE_BLOCK_PATTERN.findall(path.read_text()))


class SimulatedTerraformTool(Tool):
    @property
    def name(self) -> str:
        return "terraform"

    @property
    def operations(self) -> tuple[ToolOperationSpec, ...]:
        return _OPERATIONS

    def execute(
        self,
        operation: str,
        params: Mapping[str, Any],
        *,
        dry_run: bool,
        approval: ApprovalRecord | None,
    ) -> ToolResult:
        spec = self.spec_for(operation)
        ensure_approved(self.name, spec, dry_run=dry_run, approval=approval)

        details: dict[str, Any] = {}
        if operation == "fmt":
            summary = "Configuration already formatted (simulated)"
        elif operation == "validate":
            summary = "Success! The configuration is valid. (simulated)"
        elif operation == "plan":
            create_count = _count_declared_resources()
            summary = f"Plan: {create_count} to add, 0 to change, 0 to destroy. (simulated)"
            details = {"create": create_count, "change": 0, "destroy": 0}
        elif operation == "apply_approved_plan":
            create_count = _count_declared_resources()
            summary = (
                f"Apply complete! Resources: {create_count} added, 0 changed, "
                "0 destroyed. (simulated)"
            )
            details = {"created": create_count}
        else:  # destroy_approved_environment
            summary = "Destroy complete! Resources: all destroyed. (simulated)"
            details = {"destroyed": True}

        return ToolResult(
            success=True,
            summary=summary,
            details=details,
            risk_level=spec.risk_level,
            was_dry_run=dry_run,
            approval=approval,
        )
