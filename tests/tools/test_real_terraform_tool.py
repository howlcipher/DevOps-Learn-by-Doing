import json
import os
from pathlib import Path

from devops_learn.tools.approval import ApprovalRecord
from devops_learn.tools.base import RiskLevel
from devops_learn.tools.terraform_tool import RealTerraformTool
from devops_learn.validation import terraform_plan_analysis

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "fake_terraform"


def _use_fake_terraform(monkeypatch, scenario: str = "success") -> None:
    monkeypatch.setenv("PATH", f"{FIXTURES_DIR}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("FAKE_TERRAFORM_SCENARIO", scenario)


def test_real_terraform_tool_declares_real_apply_and_destroy_risk() -> None:
    tool = RealTerraformTool()
    assert tool.name == "terraform"
    names = {spec.name for spec in tool.operations}
    assert names == {
        "fmt",
        "init",
        "validate",
        "plan",
        "output",
        "apply_approved_plan",
        "destroy_approved_environment",
    }
    for spec in tool.operations:
        if spec.name in {"apply_approved_plan", "destroy_approved_environment"}:
            assert spec.requires_approval
            continue
        assert spec.risk_level is RiskLevel.SAFE
        assert not spec.requires_approval


def test_real_terraform_tool_apply_and_destroy_require_approval() -> None:
    tool = RealTerraformTool()
    assert tool.spec_for("apply_approved_plan").risk_level is RiskLevel.HIGH
    assert tool.spec_for("destroy_approved_environment").risk_level is RiskLevel.DESTRUCTIVE


def test_missing_binary_reports_failure(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("PATH", str(tmp_path / "empty-path"))
    (tmp_path / "empty-path").mkdir()
    result = RealTerraformTool().execute(
        "fmt", {"path": str(tmp_path)}, dry_run=False, approval=None
    )
    assert not result.success
    assert "Terraform CLI not found" in result.summary


def test_fmt_success(monkeypatch, tmp_path) -> None:
    _use_fake_terraform(monkeypatch)
    result = RealTerraformTool().execute(
        "fmt", {"path": str(tmp_path)}, dry_run=False, approval=None
    )
    assert result.success
    assert "(real)" in result.summary


def test_fmt_needs_formatting(monkeypatch, tmp_path) -> None:
    _use_fake_terraform(monkeypatch, "fmt_needs_formatting")
    result = RealTerraformTool().execute(
        "fmt", {"path": str(tmp_path)}, dry_run=False, approval=None
    )
    assert not result.success
    assert "needs formatting" in result.summary.lower()


def test_init_success(monkeypatch, tmp_path) -> None:
    _use_fake_terraform(monkeypatch)
    result = RealTerraformTool().execute(
        "init", {"path": str(tmp_path)}, dry_run=False, approval=None
    )
    assert result.success
    assert "(real)" in result.summary


def test_init_failure(monkeypatch, tmp_path) -> None:
    _use_fake_terraform(monkeypatch, "init_failure")
    result = RealTerraformTool().execute(
        "init", {"path": str(tmp_path)}, dry_run=False, approval=None
    )
    assert not result.success
    assert "(real, failed)" in result.summary


def test_validate_success(monkeypatch, tmp_path) -> None:
    _use_fake_terraform(monkeypatch)
    result = RealTerraformTool().execute(
        "validate", {"path": str(tmp_path)}, dry_run=False, approval=None
    )
    assert result.success
    assert "valid" in result.summary.lower()


def test_validate_failure(monkeypatch, tmp_path) -> None:
    _use_fake_terraform(monkeypatch, "validate_failure")
    result = RealTerraformTool().execute(
        "validate", {"path": str(tmp_path)}, dry_run=False, approval=None
    )
    assert not result.success
    assert result.details["diagnostic_count"] == 1


def test_plan_success_produces_classifier_shaped_details(monkeypatch, tmp_path) -> None:
    """Proves the real plan output needs zero changes to
    validation/terraform_plan_analysis.analyze()."""
    _use_fake_terraform(monkeypatch)
    result = RealTerraformTool().execute(
        "plan", {"path": str(tmp_path)}, dry_run=False, approval=None
    )
    assert result.success
    assert result.details.keys() >= {"create", "change", "replace", "destroy"}
    assert result.details["create"] == 2

    summary = terraform_plan_analysis.analyze(result.details)
    assert summary.risk_level is RiskLevel.SAFE


def test_plan_mixed_actions_classified_correctly(monkeypatch, tmp_path) -> None:
    _use_fake_terraform(monkeypatch, "plan_mixed_actions")
    result = RealTerraformTool().execute(
        "plan", {"path": str(tmp_path)}, dry_run=False, approval=None
    )
    assert result.success
    assert result.details["create"] == 1
    assert result.details["change"] == 1
    assert result.details["replace"] == 1
    assert result.details["destroy"] == 1

    summary = terraform_plan_analysis.analyze(result.details)
    assert summary.risk_level is RiskLevel.DESTRUCTIVE


def test_plan_failure_is_reported_and_secret_is_redacted(monkeypatch, tmp_path) -> None:
    _use_fake_terraform(monkeypatch, "plan_failure_with_secret")
    result = RealTerraformTool().execute(
        "plan", {"path": str(tmp_path)}, dry_run=False, approval=None
    )
    assert not result.success
    dumped = json.dumps(result.details)
    assert "super-secret-value-123" not in dumped
    assert "ARM_CLIENT_SECRET=<redacted>" in dumped


def test_plan_show_json_malformed_is_a_clean_failure(monkeypatch, tmp_path) -> None:
    _use_fake_terraform(monkeypatch, "show_json_malformed")
    result = RealTerraformTool().execute(
        "plan", {"path": str(tmp_path)}, dry_run=False, approval=None
    )
    assert not result.success
    assert "Could not parse" in result.summary


def test_plan_details_never_include_raw_attribute_values(monkeypatch, tmp_path) -> None:
    _use_fake_terraform(monkeypatch, "plan_with_sensitive_attribute")
    result = RealTerraformTool().execute(
        "plan", {"path": str(tmp_path)}, dry_run=False, approval=None
    )
    assert result.success
    assert "hunter2" not in json.dumps(result.details)


def test_timeout_is_reported_not_hung(monkeypatch, tmp_path) -> None:
    _use_fake_terraform(monkeypatch, "timeout")
    result = RealTerraformTool().execute(
        "fmt",
        {"path": str(tmp_path), "timeout_seconds": 1},
        dry_run=False,
        approval=None,
    )
    assert not result.success
    assert "timed out" in result.details.get("stderr", "").lower()


def test_invalid_working_directory_reports_failure(monkeypatch, tmp_path) -> None:
    _use_fake_terraform(monkeypatch)
    result = RealTerraformTool().execute(
        "fmt",
        {"path": str(tmp_path / "does-not-exist")},
        dry_run=False,
        approval=None,
    )
    assert not result.success


def test_saved_plan_binds_digest_source_config_and_candidate(monkeypatch, tmp_path) -> None:
    _use_fake_terraform(monkeypatch)
    tool = RealTerraformTool()
    planned = tool.execute(
        "plan",
        {"path": str(tmp_path), "source_revision": "source-a", "candidate_context": "candidate-a"},
        dry_run=False,
        approval=None,
    )
    assert planned.success
    assert Path(str(planned.details["plan_path"])).is_file()
    assert planned.details["plan_digest"]
    approved = ApprovalRecord(granted=True, approved_by="test")
    applied = tool.execute(
        "apply_approved_plan",
        {
            "path": str(tmp_path),
            "plan_path": planned.details["plan_path"],
            "source_revision": "source-a",
            "candidate_context": "candidate-a",
            "candidate_identity": "candidate-identity-a",
        },
        dry_run=False,
        approval=approved,
    )
    assert applied.success


def test_apply_refuses_changed_source_or_plan(monkeypatch, tmp_path) -> None:
    _use_fake_terraform(monkeypatch)
    tool = RealTerraformTool()
    planned = tool.execute(
        "plan",
        {"path": str(tmp_path), "source_revision": "source-a", "candidate_context": "candidate-a"},
        dry_run=False,
        approval=None,
    )
    changed_source = tool.execute(
        "apply_approved_plan",
        {
            "path": str(tmp_path),
            "plan_path": planned.details["plan_path"],
            "source_revision": "source-b",
            "candidate_context": "candidate-a",
            "candidate_identity": "candidate-identity-a",
        },
        dry_run=False,
        approval=ApprovalRecord(granted=True, approved_by="test"),
    )
    assert not changed_source.success
    Path(str(planned.details["plan_path"])).write_bytes(b"changed")
    changed_plan = tool.execute(
        "apply_approved_plan",
        {
            "path": str(tmp_path),
            "plan_path": planned.details["plan_path"],
            "source_revision": "source-a",
            "candidate_context": "candidate-a",
            "candidate_identity": "candidate-identity-a",
        },
        dry_run=False,
        approval=ApprovalRecord(granted=True, approved_by="test"),
    )
    assert not changed_plan.success


def test_apply_refuses_missing_candidate_identity(monkeypatch, tmp_path) -> None:
    _use_fake_terraform(monkeypatch)
    tool = RealTerraformTool()
    planned = tool.execute(
        "plan",
        {"path": str(tmp_path), "source_revision": "source-a", "candidate_context": "candidate-a"},
        dry_run=False,
        approval=None,
    )
    result = tool.execute(
        "apply_approved_plan",
        {
            "path": str(tmp_path),
            "plan_path": planned.details["plan_path"],
            "source_revision": "source-a",
            "candidate_context": "candidate-a",
        },
        dry_run=False,
        approval=ApprovalRecord(granted=True, approved_by="test"),
    )
    assert not result.success
    assert "candidate identity" in result.summary


def test_dry_run_never_invokes_subprocess(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("PATH", str(tmp_path))  # empty dir: would fail loudly if invoked
    result = RealTerraformTool().execute(
        "plan", {"path": str(tmp_path)}, dry_run=True, approval=None
    )
    assert result.success
    assert "dry run" in result.summary.lower()
