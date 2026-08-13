"""Opt-in acceptance test for the real Azure learning lifecycle.

This is intentionally skipped in normal CI. Setting both environment variables
is an affirmative authorization to create the low-cost lab and destroy it after
the health-check evidence has been written.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
PROJECT = REPO_ROOT / "projects" / "api_platform"
ENVIRONMENT = "azure-integration"


@pytest.mark.azure_integration
def test_real_azure_lifecycle_creates_verifies_and_cleans_up() -> None:
    if os.environ.get("RUN_AZURE_INTEGRATION_TESTS") != "1":
        pytest.skip("Set RUN_AZURE_INTEGRATION_TESTS=1 to run Azure integration tests.")
    if os.environ.get("AZURE_DEPLOYMENT_APPROVED") != "1":
        pytest.fail(
            "Set AZURE_DEPLOYMENT_APPROVED=1 to explicitly authorize this real Azure test."
        )

    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(REPO_ROOT / "src")
    deploy = [
        sys.executable,
        "-m",
        "devops_learn.cli.main",
        "deploy",
        str(PROJECT),
        "--cloud",
        "azure",
        "--environment",
        ENVIRONMENT,
    ]
    destroy = [
        sys.executable,
        "-m",
        "devops_learn.cli.main",
        "destroy",
        str(PROJECT),
        "--environment",
        ENVIRONMENT,
    ]
    approvals = "y\n" * 8
    state_path = PROJECT / "infra" / "terraform" / "terraform.tfstate"
    try:
        completed = subprocess.run(
            deploy,
            cwd=REPO_ROOT,
            env=environment,
            input=approvals,
            capture_output=True,
            text=True,
            timeout=1800,
            check=False,
        )
        output = completed.stdout + completed.stderr
        evidence_path = PROJECT / "artifacts" / "deployment" / "azure-deployment-evidence.json"
        assert completed.returncode == 0, output
        assert evidence_path.is_file(), output
        evidence = json.loads(evidence_path.read_text())
        assert evidence["status"] == "completed", output
        assert evidence["stages"]["health_verification"] == "REAL PASS", output
    finally:
        if state_path.is_file():
            cleanup = subprocess.run(
                destroy,
                cwd=REPO_ROOT,
                env=environment,
                input="y\ny\n",
                capture_output=True,
                text=True,
                timeout=900,
                check=False,
            )
            assert cleanup.returncode == 0, cleanup.stdout + cleanup.stderr
