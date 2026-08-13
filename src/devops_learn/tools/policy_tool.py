"""A narrow Conftest boundary for deterministic deployment policy."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, Mapping

from devops_learn.tools import _subprocess_safety
from devops_learn.tools.approval import ApprovalRecord
from devops_learn.tools.base import RiskLevel, Tool, ToolOperationSpec, ToolResult

_OPERATIONS = (
    ToolOperationSpec("version", RiskLevel.SAFE, False, False, False),
    ToolOperationSpec("evaluate", RiskLevel.SAFE, False, False, False),
)


def _conftest_command() -> str:
    command = shutil.which("conftest")
    if command is None:
        raise FileNotFoundError(
            "Conftest CLI not found. Install it from https://www.conftest.dev/install/."
        )
    return command


class PolicyTool(Tool):
    @property
    def name(self) -> str:
        return "security_policy"

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
                True,
                f"Would run Conftest {operation} (dry run)",
                {},
                spec.risk_level,
                True,
                approval,
            )
        try:
            conftest = _conftest_command()
            if operation == "version":
                result = _subprocess_safety.run_safely(
                    [conftest, "--version"], cwd=None, timeout=15
                )
                return ToolResult(
                    result.returncode == 0,
                    ("(real) " if result.returncode == 0 else "(real, failed) ")
                    + (result.stdout.strip() or result.stderr.strip()),
                    {"returncode": result.returncode},
                    spec.risk_level,
                    False,
                    approval,
                )
            input_path = Path(str(params["input_path"])).resolve()
            policy_path = Path(str(params["policy_path"])).resolve()
            if not input_path.is_file() or not policy_path.is_dir():
                raise ValueError("Policy input file or policy directory is unavailable.")
            result = _subprocess_safety.run_safely(
                [
                    conftest,
                    "test",
                    "--policy",
                    str(policy_path),
                    "--output",
                    "json",
                    str(input_path),
                ],
                cwd=None,
                timeout=int(params.get("timeout_seconds", 30)),
            )
            # Conftest returns 1 for policy denials. That is a successful policy
            # evaluation, not an execution error, when JSON is present.
            return ToolResult(
                result.returncode in (0, 1) and bool(result.stdout),
                "(real) Conftest policy evaluated"
                if result.returncode in (0, 1) and result.stdout
                else "(real, failed) Conftest policy evaluation failed",
                {"returncode": result.returncode, "output": result.stdout, "stderr": result.stderr},
                spec.risk_level,
                False,
                approval,
            )
        except (FileNotFoundError, OSError, ValueError) as exc:
            return ToolResult(
                False,
                f"(real, failed) {exc}",
                {"error": str(exc)},
                spec.risk_level,
                False,
                approval,
            )
