"""A narrow, real Trivy tool boundary for read-only security scans."""

from __future__ import annotations

import io
import json
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path
from typing import Any, Mapping

from devops_learn.security.redaction import redact_data
from devops_learn.tools import _subprocess_safety
from devops_learn.tools.approval import ApprovalRecord
from devops_learn.tools.base import RiskLevel, Tool, ToolOperationSpec, ToolResult

_OPERATIONS = (
    ToolOperationSpec("version", RiskLevel.SAFE, False, False, False),
    ToolOperationSpec("scan_filesystem", RiskLevel.SAFE, False, False, False),
    ToolOperationSpec("scan_config", RiskLevel.SAFE, False, False, False),
    ToolOperationSpec("scan_image", RiskLevel.SAFE, False, False, False),
)


def _trivy_command() -> str:
    command = shutil.which("trivy")
    if command is None:
        raise FileNotFoundError(
            "Trivy CLI not found. Install Trivy from "
            "https://trivy.dev/latest/getting-started/installation/."
        )
    return command


def _safe_archive_extract(archive: bytes, destination: Path) -> None:
    """Extract only ordinary, relative Git archive members."""
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:") as tar:
        for member in tar.getmembers():
            destination_path = (destination / member.name).resolve()
            if destination_path != destination and destination not in destination_path.parents:
                raise ValueError("Git archive contained an unsafe path")
            if not (member.isdir() or member.isreg()):
                raise ValueError("Git archive contained a non-regular file")
        tar.extractall(destination, filter="data")


class SecurityScannerTool(Tool):
    """Executes only allow-listed, non-destructive Trivy operations.

    A base ref is materialized as a temporary ``git archive`` rather than a
    worktree, so comparison never changes the learner's working tree.
    """

    @property
    def name(self) -> str:
        return "security_scanner"

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
        if dry_run:
            return ToolResult(
                True, f"Would run Trivy {operation} (dry run)", {}, spec.risk_level, True, approval
            )
        try:
            trivy = _trivy_command()
            if operation == "version":
                result = _subprocess_safety.run_safely([trivy, "version"], cwd=None, timeout=15)
                return ToolResult(
                    result.returncode == 0,
                    ("(real) " if result.returncode == 0 else "(real, failed) ")
                    + (result.stdout.strip() or result.stderr.strip()),
                    {"returncode": result.returncode},
                    spec.risk_level,
                    False,
                    approval,
                )
            target_value = str(params.get("target", "."))
            target = Path(target_value).resolve()
            if operation != "scan_image" and not target.is_dir():
                raise ValueError(f"Scan target is not a directory: {target}")
            timeout = int(params.get("timeout_seconds", 120))
            base_ref = params.get("base_ref")
            if base_ref is not None and operation == "scan_image":
                raise ValueError(
                    "Base comparison is supported for filesystem and config scans, not images."
                )
            if base_ref is not None:
                return self._scan_base(
                    trivy, operation, target, str(base_ref), timeout, spec, approval
                )
            scan_target = target_value if operation == "scan_image" else str(target)
            return self._scan(trivy, operation, scan_target, timeout, spec, approval)
        except (FileNotFoundError, OSError, subprocess.TimeoutExpired, ValueError) as exc:
            return ToolResult(
                False,
                f"(real, failed) {exc}",
                {"error": str(exc)},
                spec.risk_level,
                False,
                approval,
            )

    def _scan_base(
        self,
        trivy: str,
        operation: str,
        target: Path,
        base_ref: str,
        timeout: int,
        spec: ToolOperationSpec,
        approval: ApprovalRecord | None,
    ) -> ToolResult:
        repository = subprocess.run(
            ["git", "-C", str(target), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )
        if repository.returncode != 0 or not repository.stdout.strip():
            return ToolResult(
                False,
                "(real, failed) Base comparison requires a Git repository target.",
                {},
                spec.risk_level,
                False,
                approval,
            )
        repository_root = Path(repository.stdout.strip()).resolve()
        try:
            relative_target = target.relative_to(repository_root)
        except ValueError:
            return ToolResult(
                False,
                "(real, failed) Scan target is outside its Git repository.",
                {},
                spec.risk_level,
                False,
                approval,
            )
        verified = subprocess.run(
            [
                "git",
                "-C",
                str(repository_root),
                "rev-parse",
                "--verify",
                "--end-of-options",
                f"{base_ref}^{{commit}}",
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )
        if verified.returncode != 0:
            return ToolResult(
                False,
                "(real, failed) Base ref does not resolve to a commit.",
                {"base_ref": base_ref},
                spec.risk_level,
                False,
                approval,
            )
        archived = subprocess.run(
            ["git", "-C", str(repository_root), "archive", "--format=tar", "--", base_ref],
            capture_output=True,
            check=False,
            timeout=30,
        )
        if archived.returncode != 0:
            return ToolResult(
                False,
                "(real, failed) Could not archive the base ref.",
                {"base_ref": base_ref},
                spec.risk_level,
                False,
                approval,
            )
        with tempfile.TemporaryDirectory(prefix="devops-learn-security-") as directory:
            base_dir = Path(directory)
            _safe_archive_extract(archived.stdout, base_dir)
            result = self._scan(
                trivy,
                operation,
                str(base_dir / relative_target),
                timeout,
                spec,
                approval,
            )
            details = dict(result.details)
            details["base_ref"] = base_ref
            details["scanned_state"] = "base"
            return ToolResult(
                result.success,
                result.summary,
                details,
                result.risk_level,
                result.was_dry_run,
                result.approval,
            )

    def _scan(
        self,
        trivy: str,
        operation: str,
        target: str,
        timeout: int,
        spec: ToolOperationSpec,
        approval: ApprovalRecord | None,
    ) -> ToolResult:
        if operation == "scan_filesystem":
            command = [
                trivy,
                "fs",
                "--format",
                "json",
                "--quiet",
                "--scanners",
                "vuln,secret",
            ]
            secret_config = Path(target) / "trivy-secret.yaml"
            if secret_config.is_file():
                command.extend(["--secret-config", str(secret_config)])
            command.append(target)
        elif operation == "scan_config":
            command = [trivy, "config", "--format", "json", "--quiet", target]
        else:
            command = [trivy, "image", "--format", "json", "--quiet", target]
        result = _subprocess_safety.run_safely(command, cwd=None, timeout=timeout)
        try:
            parsed = json.loads(result.stdout) if result.stdout else {}
        except json.JSONDecodeError:
            parsed = None
        if result.returncode != 0 or not isinstance(parsed, dict):
            reason = "Trivy returned malformed JSON" if parsed is None else "Trivy scan failed"
            return ToolResult(
                False,
                f"(real, failed) {reason}",
                {"returncode": result.returncode, "stderr": result.stderr},
                spec.risk_level,
                False,
                approval,
            )
        safe_scan = redact_data(parsed)
        return ToolResult(
            True,
            "(real) Trivy scan completed",
            {"scan": safe_scan, "returncode": result.returncode},
            spec.risk_level,
            False,
            approval,
        )
