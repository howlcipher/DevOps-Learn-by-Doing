#!/usr/bin/env python3
"""PreToolUse hook: forces explicit user confirmation before a Bash command
that could destroy infrastructure or discard history runs, instead of
letting it execute silently.

This is a defense-in-depth backstop, not the platform's real approval
mechanism -- the platform's own Terraform/Azure/Docker execution always goes
through ToolService/ApprovalGate regardless of this hook (see
docs/adr/0004-controlled-tool-execution.md). This hook only matters when a
command bypasses that layer entirely, e.g. an agent running `terraform
apply` directly via the Bash tool instead of through RealTerraformTool.

Reads the PreToolUse JSON payload from stdin, and if tool_input.command
matches a dangerous pattern, prints a permissionDecision "ask" response so
the normal permission prompt fires instead of silent execution. Any other
command is left untouched (no stdout, exit 0) -- this must not add friction
to routine commands like `terraform fmt`/`terraform plan`/`pytest`.
"""
from __future__ import annotations

import json
import re
import sys

_DANGEROUS_PATTERNS = (
    r"\bterraform\s+apply\b",
    r"\bterraform\s+destroy\b",
    r"\bterraform\s+state\s+rm\b",
    r"\baz\s+group\s+delete\b",
    r"\baz\s+resource\s+delete\b",
    r"\baz\s+role\s+assignment\s+(create|delete)\b",
    r"\brm\s+.*terraform\.tfstate",
    r"\brm\s+-rf\s+.*\.terraform\b",
    r"\bgit\s+push\b.*(--force\b|(?<!\S)-f\b)",
)
_COMPILED = re.compile("|".join(_DANGEROUS_PATTERNS), re.IGNORECASE)


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    tool_input = payload.get("tool_input") if isinstance(payload, dict) else None
    command = tool_input.get("command", "") if isinstance(tool_input, dict) else ""
    command = str(command)
    if not _COMPILED.search(command):
        return 0

    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "ask",
                    "permissionDecisionReason": (
                        "This command can destroy infrastructure or discard history "
                        "outside the platform's own ToolService approval gate. "
                        "Confirm you intend to run it before proceeding."
                    ),
                }
            }
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
