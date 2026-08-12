"""TerraformTool implementations: simulated (no binary invoked, used by
`analyze`/`review`) and real (used by `devops-learn terraform`).

SimulatedTerraformTool.plan() derives its resource count from
templates/terraform/main.tf.reference instead of a hardcoded string, so the
learner's interpretation question stays meaningful and the reference config
can change without a second edit site.

RealTerraformTool shells out to a real `terraform` binary for fmt/init/
validate/plan only -- see its class docstring for why apply/destroy are
deliberately not declared here. Its plan parsing never extracts raw resource
attribute values (before/after) from `terraform show -json`, only
{address, action} pairs: this is the primary defense against leaking
sensitive plan data, since Terraform's own "sensitive" markers can vary by
provider/version and are not a defense to rely on alone. Free-text
stdout/stderr from every real subprocess call is still redacted and
truncated via tools/_subprocess_safety.py as defense in depth.
"""

from __future__ import annotations

import json
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any, Mapping

from devops_learn.tools import _subprocess_safety
from devops_learn.tools.approval import ApprovalRecord
from devops_learn.tools.base import RiskLevel, Tool, ToolOperationSpec, ToolResult

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
        assert not spec.requires_approval or dry_run or (approval is not None and approval.granted)

        details: dict[str, Any] = {}
        if operation == "fmt":
            summary = "Configuration already formatted (simulated)"
        elif operation == "validate":
            summary = "Success! The configuration is valid. (simulated)"
        elif operation == "plan":
            create_count = _count_declared_resources()
            replace_count = int(params.get("simulate_replace", 0))
            create_count = max(create_count - replace_count, 0)
            summary = (
                f"Plan: {create_count} to add, 0 to change, {replace_count} to replace, "
                "0 to destroy. (simulated)"
            )
            details = {
                "create": create_count,
                "change": 0,
                "replace": replace_count,
                "destroy": 0,
            }
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


_REAL_OPERATIONS = (
    ToolOperationSpec(
        name="fmt",
        risk_level=RiskLevel.SAFE,
        supports_dry_run=False,
        requires_approval=False,
        is_destructive=False,
    ),
    ToolOperationSpec(
        name="init",
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
)


def _terraform_command() -> str:
    command = shutil.which("terraform")
    if command is None:
        raise FileNotFoundError(
            "Terraform CLI not found. Install Terraform or use simulation mode."
        )
    return command


def _details_from_plan_json(plan_json: Mapping[str, Any]) -> dict[str, Any]:
    """Extracts only {address, action} pairs from a real `terraform show -json`
    plan -- never the resource_changes[].change.before/after attribute maps,
    which can contain sensitive values. See the module docstring."""
    create = change = replace = destroy = 0
    resources: list[dict[str, str]] = []
    for resource_change in plan_json.get("resource_changes", []):
        actions = tuple(resource_change.get("change", {}).get("actions", ()))
        if actions == ("create",):
            create += 1
            action = "create"
        elif actions == ("update",):
            change += 1
            action = "update"
        elif actions in (("delete", "create"), ("create", "delete")):
            replace += 1
            action = "replace"
        elif actions == ("delete",):
            destroy += 1
            action = "destroy"
        else:
            continue  # ("no-op",) / ("read",): not a change
        address = str(resource_change.get("address", "unknown"))
        resources.append({"address": address, "action": action})
    return {
        "create": create,
        "change": change,
        "replace": replace,
        "destroy": destroy,
        "resources": resources,
    }


class RealTerraformTool(Tool):
    """Runs real terraform fmt/init/validate/plan via subprocess.

    Deliberately does not declare apply_approved_plan or
    destroy_approved_environment: those stay simulated until Milestone 3, per
    docs/roadmap.md. A caller invoking either operation on this tool gets a
    KeyError from Tool.spec_for rather than a result that looks real but
    silently isn't -- apply/destroy remain real capabilities of the
    "terraform" tool name only via SimulatedTerraformTool, exactly how
    cli/main.py already selects real-vs-simulated per command today. See
    docs/adr/0004-controlled-tool-execution.md.
    """

    @property
    def name(self) -> str:
        return "terraform"

    @property
    def operations(self) -> tuple[ToolOperationSpec, ...]:
        return _REAL_OPERATIONS

    def execute(
        self,
        operation: str,
        params: Mapping[str, Any],
        *,
        dry_run: bool,
        approval: ApprovalRecord | None,
    ) -> ToolResult:
        spec = self.spec_for(operation)
        assert not spec.requires_approval or dry_run or (approval is not None and approval.granted)

        if dry_run:
            return ToolResult(
                success=True,
                summary=f"Would run terraform {operation} (dry run)",
                details={"dry_run": True},
                risk_level=spec.risk_level,
                was_dry_run=dry_run,
                approval=approval,
            )

        working_dir = params.get("path")
        timeout_override = params.get("timeout_seconds")

        def _timeout(default: int) -> int:
            return int(timeout_override) if timeout_override is not None else default

        try:
            terraform = _terraform_command()
            if operation == "fmt":
                result = _subprocess_safety.run_safely(
                    [terraform, "fmt", "-check", "-diff", "-no-color"],
                    cwd=working_dir,
                    timeout=_timeout(30),
                )
                success = result.returncode == 0
                summary = "Configuration already formatted" if success else (
                    "Configuration needs formatting"
                )
                details: dict[str, Any] = {
                    "returncode": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                }
            elif operation == "init":
                result = _subprocess_safety.run_safely(
                    [terraform, "init", "-input=false", "-no-color"],
                    cwd=working_dir,
                    timeout=_timeout(120),
                )
                success = result.returncode == 0
                success_lines = [
                    line
                    for line in result.stdout.strip().splitlines()
                    if "successfully initialized" in line.lower()
                ]
                if success_lines:
                    summary = success_lines[0].strip()
                elif success:
                    summary = "Terraform has been initialized"
                else:
                    summary = "terraform init failed"
                details = {
                    "returncode": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                }
            elif operation == "validate":
                result = _subprocess_safety.run_safely(
                    [terraform, "validate", "-json"], cwd=working_dir, timeout=_timeout(30)
                )
                try:
                    parsed = json.loads(result.stdout) if result.stdout else {}
                except json.JSONDecodeError:
                    parsed = {}
                diagnostics = parsed.get("diagnostics", [])
                success = result.returncode == 0 and bool(parsed.get("valid", False))
                summary = (
                    "Success! The configuration is valid."
                    if success
                    else f"Validation failed: {len(diagnostics)} diagnostic(s)"
                )
                details = {
                    "returncode": result.returncode,
                    "valid": parsed.get("valid"),
                    "diagnostic_count": len(diagnostics),
                    "stderr": result.stderr,
                }
            else:  # plan
                with tempfile.TemporaryDirectory() as tmp_dir:
                    plan_path = str(Path(tmp_dir) / "tfplan.out")
                    plan_result = _subprocess_safety.run_safely(
                        [terraform, "plan", "-input=false", "-no-color", f"-out={plan_path}"],
                        cwd=working_dir,
                        timeout=_timeout(180),
                    )
                    if plan_result.returncode != 0:
                        return ToolResult(
                            success=False,
                            summary="(real, failed) terraform plan failed",
                            details={
                                "returncode": plan_result.returncode,
                                "stdout": plan_result.stdout,
                                "stderr": plan_result.stderr,
                            },
                            risk_level=spec.risk_level,
                            was_dry_run=dry_run,
                            approval=approval,
                        )
                    show_result = _subprocess_safety.run_safely(
                        [terraform, "show", "-json", plan_path], cwd=working_dir, timeout=30
                    )
                    if show_result.returncode != 0:
                        return ToolResult(
                            success=False,
                            summary="(real, failed) terraform show -json failed",
                            details={
                                "returncode": show_result.returncode,
                                "stderr": show_result.stderr,
                            },
                            risk_level=spec.risk_level,
                            was_dry_run=dry_run,
                            approval=approval,
                        )
                    try:
                        plan_json = json.loads(show_result.stdout)
                    except json.JSONDecodeError:
                        return ToolResult(
                            success=False,
                            summary="(real, failed) Could not parse terraform show -json output",
                            details={"error": "malformed JSON from terraform show -json"},
                            risk_level=spec.risk_level,
                            was_dry_run=dry_run,
                            approval=approval,
                        )
                    details = _details_from_plan_json(plan_json)
                    success = True
                    summary = (
                        f"Plan: {details['create']} to add, {details['change']} to change, "
                        f"{details['replace']} to replace, {details['destroy']} to destroy."
                    )
        except (OSError, FileNotFoundError) as exc:
            return ToolResult(
                success=False,
                summary=f"(real, failed) {exc}",
                details={"error": str(exc)},
                risk_level=spec.risk_level,
                was_dry_run=dry_run,
                approval=approval,
            )

        prefix = "(real) " if success else "(real, failed) "
        return ToolResult(
            success=success,
            summary=prefix + summary,
            details=details,
            risk_level=spec.risk_level,
            was_dry_run=dry_run,
            approval=approval,
        )
