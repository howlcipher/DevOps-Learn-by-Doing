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
from datetime import datetime, timezone
from hashlib import sha256
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
    ToolOperationSpec("output", RiskLevel.SAFE, False, False, False),
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
    ToolOperationSpec("output", RiskLevel.SAFE, False, False, False),
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


def _terraform_command() -> str:
    command = shutil.which("terraform")
    if command is None:
        raise FileNotFoundError(
            "Terraform CLI not found. Install Terraform or use simulation mode."
        )
    return command


def _digest_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def terraform_config_digest(working_dir: Path) -> str:
    """Hash committed Terraform inputs, never state or generated provider files."""
    digest = sha256()
    paths = sorted(
        [*working_dir.glob("*.tf"), working_dir / ".terraform.lock.hcl"],
        key=lambda path: path.name,
    )
    for path in paths:
        if not path.is_file():
            continue
        digest.update(path.name.encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _controlled_plan_path(working_dir: Path, value: object | None) -> Path:
    artifacts = (working_dir / ".devops_learn" / "plans").resolve()
    candidate = Path(str(value)).resolve() if value is not None else artifacts / "terraform.tfplan"
    if candidate.parent != artifacts or candidate.suffix != ".tfplan":
        raise ValueError("Saved plans must be direct .tfplan files in .devops_learn/plans.")
    artifacts.mkdir(parents=True, exist_ok=True)
    return candidate


def _plan_metadata_path(plan_path: Path) -> Path:
    return plan_path.with_suffix(".tfplan.json")


def _variable_args(params: Mapping[str, Any]) -> list[str]:
    variables = params.get("variables", {})
    if not isinstance(variables, Mapping):
        raise ValueError("Terraform variables must be a mapping.")
    allowed = {"deploy_application", "app_image"}
    if set(variables) - allowed:
        raise ValueError("Only deploy_application and app_image are accepted by this workflow.")
    args: list[str] = []
    for name in sorted(variables):
        value = variables[name]
        if name == "deploy_application" and not isinstance(value, bool):
            raise ValueError("deploy_application must be boolean.")
        if name == "app_image" and (not isinstance(value, str) or "@sha256:" not in value):
            raise ValueError("app_image must be a digest-pinned image reference.")
        args.extend(["-var", f"{name}={str(value).lower() if isinstance(value, bool) else value}"])
    return args


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
    """Runs real Terraform only through bounded, auditable operations.

    Saved plans live under the working directory's ``.devops_learn/plans``.
    Apply reads a metadata sidecar created by this tool and rejects a plan,
    source, config, candidate, or digest mismatch before invoking Terraform.
    There is no real-to-simulated fallback.
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

        working_dir_value = params.get("path")
        if not isinstance(working_dir_value, str) or not Path(working_dir_value).is_dir():
            return ToolResult(
                False,
                "(real, failed) Terraform working directory is unavailable.",
                {},
                spec.risk_level,
                dry_run,
                approval,
            )
        working_dir = str(Path(working_dir_value).resolve())
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
                summary = (
                    "Configuration already formatted"
                    if success
                    else ("Configuration needs formatting")
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
            elif operation == "plan":
                plan_path = _controlled_plan_path(Path(working_dir), params.get("plan_path"))
                plan_result = _subprocess_safety.run_safely(
                    [
                        terraform,
                        "plan",
                        "-input=false",
                        "-no-color",
                        *_variable_args(params),
                        f"-out={plan_path}",
                    ],
                    cwd=working_dir,
                    timeout=_timeout(180),
                )
                if plan_result.returncode != 0:
                    return ToolResult(
                        False,
                        "(real, failed) terraform plan failed",
                        {
                            "returncode": plan_result.returncode,
                            "stdout": plan_result.stdout,
                            "stderr": plan_result.stderr,
                        },
                        spec.risk_level,
                        dry_run,
                        approval,
                    )
                show_result = _subprocess_safety.run_safely(
                    [terraform, "show", "-json", str(plan_path)], cwd=working_dir, timeout=30
                )
                if show_result.returncode != 0:
                    return ToolResult(
                        False,
                        "(real, failed) terraform show -json failed",
                        {
                            "returncode": show_result.returncode,
                            "stderr": show_result.stderr,
                        },
                        spec.risk_level,
                        dry_run,
                        approval,
                    )
                try:
                    plan_json = json.loads(show_result.stdout)
                except json.JSONDecodeError:
                    return ToolResult(
                        False,
                        "(real, failed) Could not parse terraform show -json output",
                        {"error": "malformed JSON from terraform show -json"},
                        spec.risk_level,
                        dry_run,
                        approval,
                    )
                details = _details_from_plan_json(plan_json)
                plan_digest = _digest_file(plan_path)
                metadata = {
                    "candidate_context": params.get("candidate_context"),
                    "config_digest": terraform_config_digest(Path(working_dir)),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "plan_digest": plan_digest,
                    "source_revision": params.get("source_revision"),
                }
                _plan_metadata_path(plan_path).write_text(
                    json.dumps(metadata, sort_keys=True) + "\n"
                )
                details.update(
                    {"plan_path": str(plan_path), "plan_digest": plan_digest, **metadata}
                )
                success = True
                summary = (
                    f"Plan: {details['create']} to add, {details['change']} to change, "
                    f"{details['replace']} to replace, {details['destroy']} to destroy."
                )
            elif operation == "output":
                result = _subprocess_safety.run_safely(
                    [terraform, "output", "-json"], cwd=working_dir, timeout=_timeout(30)
                )
                try:
                    raw_outputs = json.loads(result.stdout) if result.stdout else {}
                except json.JSONDecodeError:
                    raw_outputs = {}
                details = {
                    name: value.get("value")
                    for name, value in raw_outputs.items()
                    if name
                    in {
                        "resource_group_name",
                        "container_registry_login_server",
                        "container_app_environment_name",
                        "container_app_name",
                        "container_app_endpoint",
                    }
                    and isinstance(value, dict)
                }
                success = result.returncode == 0
                summary = "Terraform outputs collected" if success else "terraform output failed"
            elif operation == "apply_approved_plan":
                return self._apply(
                    terraform, Path(working_dir), params, spec, approval, _timeout(300)
                )
            else:
                return self._destroy(terraform, working_dir, params, spec, approval, _timeout(300))
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

    def _apply(
        self,
        terraform: str,
        working_dir: Path,
        params: Mapping[str, Any],
        spec: ToolOperationSpec,
        approval: ApprovalRecord | None,
        timeout: int,
    ) -> ToolResult:
        try:
            plan_path = _controlled_plan_path(working_dir, params.get("plan_path"))
            metadata = json.loads(_plan_metadata_path(plan_path).read_text())
            expected = {
                "candidate_context": params.get("candidate_context"),
                "source_revision": params.get("source_revision"),
                "config_digest": terraform_config_digest(working_dir),
                "plan_digest": _digest_file(plan_path),
            }
            if any(not value or metadata.get(key) != value for key, value in expected.items()):
                return ToolResult(
                    False,
                    "(real, refused) approved plan evidence is stale or changed",
                    {"reason": "candidate, source, configuration, or plan digest did not match"},
                    spec.risk_level,
                    False,
                    approval,
                )
            result = _subprocess_safety.run_safely(
                [terraform, "apply", "-input=false", "-no-color", str(plan_path)],
                cwd=str(working_dir),
                timeout=timeout,
            )
            return ToolResult(
                result.returncode == 0,
                "(real) approved Terraform plan applied"
                if result.returncode == 0
                else "(real, failed) terraform apply failed",
                {
                    "returncode": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "plan_digest": expected["plan_digest"],
                },
                spec.risk_level,
                False,
                approval,
            )
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            return ToolResult(
                False,
                f"(real, refused) {exc}",
                {"error": str(exc)},
                spec.risk_level,
                False,
                approval,
            )

    def _destroy(
        self,
        terraform: str,
        working_dir: str,
        params: Mapping[str, Any],
        spec: ToolOperationSpec,
        approval: ApprovalRecord | None,
        timeout: int,
    ) -> ToolResult:
        if not params.get("resource_group") or not params.get("environment"):
            return ToolResult(
                False,
                "(real, refused) destroy requires resource group and environment identity",
                {},
                spec.risk_level,
                False,
                approval,
            )
        result = _subprocess_safety.run_safely(
            [terraform, "destroy", "-input=false", "-auto-approve", "-no-color"],
            cwd=working_dir,
            timeout=timeout,
        )
        return ToolResult(
            result.returncode == 0,
            "(real) Terraform environment destroyed"
            if result.returncode == 0
            else "(real, failed) terraform destroy failed",
            {
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "resource_group": str(params["resource_group"]),
                "environment": str(params["environment"]),
            },
            spec.risk_level,
            False,
            approval,
        )
