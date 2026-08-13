import os
from pathlib import Path

from devops_learn.tools.policy_tool import PolicyTool
from devops_learn.tools.security_scanner_tool import SecurityScannerTool


def _write_binary(path: Path, body: str) -> None:
    path.write_text("#!/bin/sh\n" + body)
    path.chmod(0o755)


def test_scanner_reports_missing_binary(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("PATH", str(tmp_path))
    result = SecurityScannerTool().execute(
        "scan_filesystem", {"target": str(tmp_path)}, dry_run=False, approval=None
    )
    assert not result.success
    assert "Trivy CLI not found" in result.summary


def test_scanner_redacts_valid_json_and_rejects_malformed(monkeypatch, tmp_path) -> None:
    _write_binary(
        tmp_path / "trivy",
        (
            'if [ "$FAKE_BAD" = "1" ]; then echo nope; else echo '
            '\'{"Results":[{"Target":"x","Secrets":[{"RuleID":"x",'
            '"Match":"DEVSECOPS_DEMO_ONLY_NOT_A_CREDENTIAL_9f31b7"}]}]}\'; fi'
        ),
    )
    monkeypatch.setenv("PATH", f"{tmp_path}{os.pathsep}{os.environ['PATH']}")
    result = SecurityScannerTool().execute(
        "scan_filesystem", {"target": str(tmp_path)}, dry_run=False, approval=None
    )
    assert result.success
    assert "DEVSECOPS_DEMO_ONLY" not in str(result.details)
    monkeypatch.setenv("FAKE_BAD", "1")
    malformed = SecurityScannerTool().execute(
        "scan_filesystem", {"target": str(tmp_path)}, dry_run=False, approval=None
    )
    assert not malformed.success


def test_scanner_reports_version_failure_and_timeout(monkeypatch, tmp_path) -> None:
    _write_binary(
        tmp_path / "trivy",
        'if [ "$1" = "version" ]; then echo "Version: test"; exit 0; fi; sleep 2; echo "{}"',
    )
    monkeypatch.setenv("PATH", f"{tmp_path}{os.pathsep}{os.environ['PATH']}")
    version = SecurityScannerTool().execute("version", {}, dry_run=False, approval=None)
    assert version.success
    assert "Version: test" in version.summary
    timed_out = SecurityScannerTool().execute(
        "scan_filesystem",
        {"target": str(tmp_path), "timeout_seconds": 1},
        dry_run=False,
        approval=None,
    )
    assert not timed_out.success
    assert "timed out" in str(timed_out.details).lower()


def test_policy_tool_reports_missing_conftest(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("PATH", str(tmp_path))
    result = PolicyTool().execute("version", {}, dry_run=False, approval=None)
    assert not result.success
    assert "Conftest CLI not found" in result.summary
