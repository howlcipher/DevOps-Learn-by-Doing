"""Sanitized, verifiable lifecycle evidence reports."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from devops_learn.deployment.candidate import DeploymentCandidate
from devops_learn.security.redaction import redact_data


def write_evidence_report(
    path: Path,
    candidate: DeploymentCandidate,
    *,
    status: str,
    stages: dict[str, str],
    observed_azure: dict[str, Any] | None = None,
) -> None:
    """Persist facts only; raw tool output and secrets are intentionally absent."""
    path.parent.mkdir(parents=True, exist_ok=True)
    document = {
        "candidate_identity": candidate.identity,
        "candidate": asdict(candidate),
        "status": status,
        "stages": stages,
        "observed_azure": observed_azure or {},
    }
    path.write_text(json.dumps(redact_data(document), indent=2, sort_keys=True, default=str) + "\n")
