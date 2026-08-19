"""GoTool implementations: simulated for tests/no-Go environments, and
real for local execution.

RealGoTool runs go test, go vet, go build, gofmt, and go mod verify as subprocesses
in the project directory. Every operation reports whether it is REAL or SIMULATED
in the result summary.
"""

from __future__ import annotations

import shutil
from typing import Any, Mapping

from devops_learn.tools import _subprocess_safety
from devops_learn.tools.approval import ApprovalRecord
from devops_learn.tools.base import RiskLevel, Tool, ToolOperationSpec, ToolResult

_OPERATIONS = (
    ToolOperationSpec(
        name="run_tests",
        risk_level=RiskLevel.SAFE,
        supports_dry_run=False,
        requires_approval=False,
        is_destructive=False,
    ),
    ToolOperationSpec(
        name="run_vet",
        risk_level=RiskLevel.SAFE,
        supports_dry_run=False,
        requires_approval=False,
        is_destructive=False,
    ),
    ToolOperationSpec(
        name="run_build",
        risk_level=RiskLevel.SAFE,
        supports_dry_run=False,
        requires_approval=False,
        is_destructive=False,
    ),
    ToolOperationSpec(
        name="run_fmt_check",
        risk_level=RiskLevel.SAFE,
        supports_dry_run=False,
        requires_approval=False,
        is_destructive=False,
    ),
    ToolOperationSpec(
        name="verify_modules",
        risk_level=RiskLevel.SAFE,
        supports_dry_run=False,
        requires_approval=False,
        is_destructive=False,
    ),
    ToolOperationSpec(
        name="version",
        risk_level=RiskLevel.SAFE,
        supports_dry_run=False,
        requires_approval=False,
        is_destructive=False,
    ),
)


class SimulatedGoTool(Tool):
    @property
    def name(self) -> str:
        return "go"

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

        if dry_run:
            return ToolResult(
                success=True,
                summary=f"Would run {operation} at {params.get('path', '<unknown>')} (dry run)",
                details={"dry_run": True},
                risk_level=spec.risk_level,
                was_dry_run=dry_run,
                approval=approval,
            )

        if operation == "run_tests":
            summary = "PASS: all tests passed (simulated)"
            details: dict[str, Any] = {"passed": 2, "failed": 0}
        elif operation == "run_vet":
            summary = "No vet issues found (simulated)"
            details = {"issues": 0}
        elif operation == "run_build":
            summary = "Build succeeded (simulated)"
            details = {"target": "./..."}
        elif operation == "run_fmt_check":
            summary = "All Go files are formatted (simulated)"
            details = {"unformatted": []}
        elif operation == "verify_modules":
            summary = "all modules verified (simulated)"
            details = {"verified": True}
        else:  # version
            summary = "go version go1.22.0 linux/amd64 (simulated)"
            details = {"version": "go1.22.0"}

        return ToolResult(
            success=True,
            summary=summary,
            details=details,
            risk_level=spec.risk_level,
            was_dry_run=dry_run,
            approval=approval,
        )


class RealGoTool(Tool):
    """Runs go test, go vet, go build, gofmt, and go mod verify via subprocess."""

    @property
    def name(self) -> str:
        return "go"

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

        if dry_run:
            return ToolResult(
                success=True,
                summary=f"Would run {operation} at {params.get('path', '<unknown>')} (dry run)",
                details={"dry_run": True},
                risk_level=spec.risk_level,
                was_dry_run=dry_run,
                approval=approval,
            )

        cwd: str | None = params.get("path")
        timeout = int(float(params.get("timeout", 60.0)))

        binary_name = "gofmt" if operation == "run_fmt_check" else "go"
        binary_path = shutil.which(binary_name)
        if binary_path is None:
            return ToolResult(
                success=False,
                summary=f"(real, failed) {binary_name} binary not found in PATH",
                details={"error": "not_found", "binary": binary_name},
                risk_level=spec.risk_level,
                was_dry_run=dry_run,
                approval=approval,
            )

        try:
            if operation == "run_tests":
                completed = _subprocess_safety.run_safely(
                    [binary_path, "test", "./..."], cwd=cwd, timeout=timeout
                )
                success = completed.returncode == 0
                if success:
                    lines = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
                    summary = lines[-1] if lines else "PASS"
                else:
                    summary = (
                        completed.stderr.strip()
                        or completed.stdout.strip()
                        or "test execution failed"
                    )
                details = {
                    "returncode": completed.returncode,
                    "stdout": completed.stdout,
                    "stderr": completed.stderr,
                }
            elif operation == "run_vet":
                completed = _subprocess_safety.run_safely(
                    [binary_path, "vet", "./..."], cwd=cwd, timeout=timeout
                )
                success = completed.returncode == 0
                summary = (
                    "No vet issues found"
                    if success
                    else (
                        completed.stderr.strip()
                        or completed.stdout.strip()
                        or "vet analysis failed"
                    )
                )
                details = {
                    "returncode": completed.returncode,
                    "stdout": completed.stdout,
                    "stderr": completed.stderr,
                }
            elif operation == "run_build":
                completed = _subprocess_safety.run_safely(
                    [binary_path, "build", "./..."], cwd=cwd, timeout=timeout
                )
                success = completed.returncode == 0
                summary = (
                    "Build succeeded"
                    if success
                    else (
                        completed.stderr.strip()
                        or completed.stdout.strip()
                        or "build failed"
                    )
                )
                details = {
                    "returncode": completed.returncode,
                    "stdout": completed.stdout,
                    "stderr": completed.stderr,
                }
            elif operation == "run_fmt_check":
                completed = _subprocess_safety.run_safely(
                    [binary_path, "-l", "."], cwd=cwd, timeout=timeout
                )
                unformatted = [
                    line.strip() for line in completed.stdout.splitlines() if line.strip()
                ]
                success = completed.returncode == 0 and len(unformatted) == 0
                if success:
                    summary = "All Go files are formatted"
                elif unformatted:
                    summary = f"Unformatted Go files found: {', '.join(unformatted)}"
                else:
                    summary = completed.stderr.strip() or "gofmt check failed"
                details = {
                    "returncode": completed.returncode,
                    "unformatted": unformatted,
                    "stderr": completed.stderr,
                }
            elif operation == "verify_modules":
                completed = _subprocess_safety.run_safely(
                    [binary_path, "mod", "verify"], cwd=cwd, timeout=timeout
                )
                success = completed.returncode == 0
                summary = (
                    completed.stdout.strip()
                    or ("all modules verified" if success else "module verification failed")
                )
                details = {
                    "returncode": completed.returncode,
                    "stdout": completed.stdout,
                    "stderr": completed.stderr,
                }
            else:  # version
                completed = _subprocess_safety.run_safely(
                    [binary_path, "version"], cwd=cwd, timeout=timeout
                )
                success = completed.returncode == 0
                summary = completed.stdout.strip() or "go version unknown"
                details = {
                    "returncode": completed.returncode,
                    "stdout": completed.stdout,
                    "stderr": completed.stderr,
                }

            if completed.timed_out:
                return ToolResult(
                    success=False,
                    summary=f"(real, failed) Execution timed out after {timeout}s",
                    details={"error": "timeout", "timeout": timeout},
                    risk_level=spec.risk_level,
                    was_dry_run=dry_run,
                    approval=approval,
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
