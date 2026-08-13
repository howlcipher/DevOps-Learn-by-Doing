"""PythonTool implementations: simulated for tests/no-Python environments, and
real for local execution.

RealPythonTool runs pytest/flake8/mypy as subprocesses in the project directory.
Every operation reports whether it is REAL or SIMULATED in the result summary.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping

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
        name="run_lint",
        risk_level=RiskLevel.SAFE,
        supports_dry_run=False,
        requires_approval=False,
        is_destructive=False,
    ),
    ToolOperationSpec(
        name="run_typecheck",
        risk_level=RiskLevel.SAFE,
        supports_dry_run=False,
        requires_approval=False,
        is_destructive=False,
    ),
)


def _python_executable() -> str:
    """Use the interpreter running the platform, not an unrelated system Python."""
    return sys.executable or shutil.which("python3") or shutil.which("python") or "python"


def _run(
    command: list[str], *, cwd: str | None, check: bool = False
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    # User-installed pytest plugins are outside a scanned project's dependency
    # boundary and can make an otherwise valid local workflow non-deterministic.
    environment.setdefault("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    return subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=check,
        env=environment,
    )


class SimulatedPythonTool(Tool):
    @property
    def name(self) -> str:
        return "python"

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

        if operation == "run_tests":
            summary = "3 passed in 0.04s (simulated)"
            details: dict[str, Any] = {"passed": 3, "failed": 0}
        elif operation == "run_lint":
            summary = "No lint issues found (simulated)"
            details = {"issues": 0}
        else:  # run_typecheck
            summary = "No type issues found (simulated)"
            details = {"issues": 0}

        return ToolResult(
            success=True,
            summary=summary,
            details=details,
            risk_level=spec.risk_level,
            was_dry_run=dry_run,
            approval=approval,
        )


class RealPythonTool(Tool):
    """Runs pytest, flake8, and mypy via subprocess in the supplied project root."""

    @property
    def name(self) -> str:
        return "python"

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
        try:
            if operation == "run_tests":
                tests_path = (Path(cwd or ".").resolve() / "tests")
                command = [_python_executable(), "-m", "pytest", str(tests_path)]
                completed = _run(command, cwd=cwd)
                success = completed.returncode == 0
                summary = (
                    completed.stdout.strip().splitlines()[-1] if completed.stdout else "no output"
                )
                details = {"returncode": completed.returncode, "stderr": completed.stderr}
            elif operation == "run_lint":
                lint_paths = params.get("paths", ["src", "tests"])
                command = ["flake8", "--jobs", "1"] + lint_paths
                completed = _run(command, cwd=cwd)
                success = completed.returncode == 0
                summary = completed.stdout.strip() or "No lint issues found"
                details = {"returncode": completed.returncode, "stderr": completed.stderr}
            else:  # run_typecheck
                command = ["mypy"]
                completed = _run(command, cwd=cwd)
                success = completed.returncode == 0
                summary = completed.stdout.strip() or "No type issues found"
                details = {"returncode": completed.returncode, "stderr": completed.stderr}
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
