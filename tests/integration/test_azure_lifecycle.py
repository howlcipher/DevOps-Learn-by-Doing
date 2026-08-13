"""Opt-in acceptance test for the real Azure learning lifecycle.

This is intentionally skipped in normal CI. Setting both environment variables
is an affirmative authorization to create the low-cost lab and destroy it after
the health-check evidence has been written.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
PROJECT = REPO_ROOT / "projects" / "api_platform"
ENVIRONMENT = "azure-integration"
RESOURCE_GROUP = f"api-platform-{ENVIRONMENT}-rg"


@dataclass(frozen=True)
class ResourceGroupInspection:
    """Sanitized, independent Azure cleanup observation for this lab only."""

    verified: bool
    exists: bool
    resource_ids: tuple[str, ...] = ()
    error: str = ""


def _inspect_resource_group(resource_group: str) -> ResourceGroupInspection:
    """Read only the exact resource group and its resource IDs from Azure."""
    try:
        group = subprocess.run(
            ["az", "group", "exists", "--name", resource_group, "--only-show-errors"],
            capture_output=True,
            text=True,
            timeout=45,
            check=False,
        )
    except OSError as exc:
        return ResourceGroupInspection(False, False, error=f"Azure CLI unavailable: {exc}")
    if group.returncode != 0:
        return ResourceGroupInspection(
            False,
            False,
            error=f"Azure resource-group query returned exit code {group.returncode}",
        )
    exists_output = group.stdout.strip().lower()
    if exists_output not in {"true", "false"}:
        return ResourceGroupInspection(
            False,
            False,
            error="Azure resource-group query returned an unexpected response.",
        )
    if exists_output == "false":
        return ResourceGroupInspection(True, False)

    resources = subprocess.run(
        [
            "az",
            "resource",
            "list",
            "--resource-group",
            resource_group,
            "--query",
            "[].id",
            "--output",
            "tsv",
            "--only-show-errors",
        ],
        capture_output=True,
        text=True,
        timeout=45,
        check=False,
    )
    if resources.returncode != 0:
        return ResourceGroupInspection(
            True,
            True,
            error=f"Azure resource inventory query returned exit code {resources.returncode}",
        )
    return ResourceGroupInspection(
        True,
        True,
        tuple(line for line in resources.stdout.splitlines() if line),
    )


def _remaining_resources(resource_group: str, inspection: ResourceGroupInspection) -> str:
    """Return safe, actionable identifiers without exposing Azure CLI diagnostics."""
    identifiers = [f"resource group: {resource_group}", *inspection.resource_ids]
    if inspection.error:
        identifiers.append(f"resource inventory: {inspection.error}")
    return "\n".join(identifiers)


def _assert_cleaned(
    resource_group: str, destroy_result: subprocess.CompletedProcess[str] | None
) -> None:
    """Require independent Azure proof after every attempted deployment."""
    inspection = _inspect_resource_group(resource_group)
    if not inspection.verified:
        pytest.fail(
            "AZURE CLEANUP: UNVERIFIED\n"
            f"Could not query {resource_group}: {inspection.error}"
        )
    if inspection.exists:
        pytest.fail(
            "AZURE CLEANUP: UNVERIFIED\n"
            "Remaining Azure learning resources:\n"
            f"{_remaining_resources(resource_group, inspection)}"
        )
    print("AZURE CLEANUP: VERIFIED")
    if destroy_result is not None and destroy_result.returncode != 0:
        pytest.fail(
            "AZURE CLEANUP: VERIFIED, but the approved destroy command failed. "
            "Inspect the captured lifecycle output before re-running."
        )


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
    preexisting = _inspect_resource_group(RESOURCE_GROUP)
    if not preexisting.verified:
        pytest.fail(
            "AZURE ACCEPTANCE PREFLIGHT FAILED\n"
            f"Could not query {RESOURCE_GROUP}: {preexisting.error}"
        )
    if preexisting.exists:
        pytest.fail(
            "AZURE ACCEPTANCE REFUSED\n"
            "The test resource group already exists, so it may not belong to this run:\n"
            f"{_remaining_resources(RESOURCE_GROUP, preexisting)}"
        )
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
        inspection = _inspect_resource_group(RESOURCE_GROUP)
        cleanup: subprocess.CompletedProcess[str] | None = None
        if inspection.verified and inspection.exists:
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
        _assert_cleaned(RESOURCE_GROUP, cleanup)


def test_azure_resource_group_name_is_scoped_to_the_acceptance_environment() -> None:
    assert RESOURCE_GROUP == "api-platform-azure-integration-rg"


def test_resource_group_inspection_reports_only_resource_identifiers(monkeypatch) -> None:
    responses = iter(
        (
            subprocess.CompletedProcess([], 0, stdout="true\n", stderr=""),
            subprocess.CompletedProcess(
                [],
                0,
                stdout="/subscriptions/example/resourceGroups/api-platform-azure-integration-rg\n",
                stderr="",
            ),
        )
    )
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: next(responses))

    inspection = _inspect_resource_group(RESOURCE_GROUP)

    assert inspection.verified
    assert inspection.exists
    assert inspection.resource_ids == (
        "/subscriptions/example/resourceGroups/api-platform-azure-integration-rg",
    )


def test_cleanup_requires_independent_azure_absence(monkeypatch) -> None:
    monkeypatch.setattr(
        sys.modules[__name__],
        "_inspect_resource_group",
        lambda resource_group: ResourceGroupInspection(
            True,
            True,
            (f"/resourceGroups/{resource_group}",),
        ),
    )

    with pytest.raises(pytest.fail.Exception, match="AZURE CLEANUP: UNVERIFIED"):
        _assert_cleaned(RESOURCE_GROUP, None)
