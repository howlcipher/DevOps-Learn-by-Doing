"""Shared subprocess-safety helpers for Real*Tool implementations.

Extracted because RealTerraformTool needs both an explicit timeout and output
redaction, neither of which RealDockerTool/RealPythonTool have today: those
two tools never set a subprocess timeout and put stdout/stderr into
ToolResult.details verbatim. That gap matters more for Terraform, since
provider auth errors and init/plan output can contain secret-shaped values.
Deliberately generic (no Terraform-specific knowledge) so those two tools
could adopt it later; retrofitting them is out of scope for this milestone.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass

DEFAULT_TIMEOUT_SECONDS = 120
MAX_OUTPUT_CHARS = 20_000

_SECRET_PATTERN = re.compile(
    r"(?i)\b([A-Z0-9_]*(?:SECRET|TOKEN|PASSWORD|API_KEY)[A-Z0-9_]*)\s*[=:]\s*(\S+)"
)


@dataclass(frozen=True)
class SafeRunResult:
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool


def redact(text: str) -> str:
    """Masks KEY=value-shaped secrets in free text.

    Defense in depth only. The primary defense against leaking sensitive
    Terraform data is never extracting attribute values from structured
    output in the first place -- see the module docstring in
    tools/terraform_tool.py for why plan parsing never touches
    resource_changes[].change.before/after.
    """
    return _SECRET_PATTERN.sub(lambda m: f"{m.group(1)}=<redacted>", text)


def _truncate(text: str) -> str:
    if len(text) <= MAX_OUTPUT_CHARS:
        return text
    hidden = len(text) - MAX_OUTPUT_CHARS
    return text[:MAX_OUTPUT_CHARS] + f"\n... [truncated, {hidden} more characters] ...\n"


def _sanitize(text: str) -> str:
    return _truncate(redact(text))


def run_safely(
    command: list[str], *, cwd: str | None, timeout: int = DEFAULT_TIMEOUT_SECONDS
) -> SafeRunResult:
    """Runs `command` as an argument array (never shell=True) with a timeout,
    and always redacts + truncates stdout/stderr before returning, so a call
    site can never forget to sanitize output before it reaches a ToolResult.
    """
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        partial_stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        return SafeRunResult(
            returncode=-1,
            stdout=_sanitize(partial_stdout),
            stderr=_sanitize(f"Command timed out after {timeout}s: {' '.join(command)}"),
            timed_out=True,
        )
    return SafeRunResult(
        returncode=completed.returncode,
        stdout=_sanitize(completed.stdout),
        stderr=_sanitize(completed.stderr),
        timed_out=False,
    )
