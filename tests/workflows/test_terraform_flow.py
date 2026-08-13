import os
import sqlite3
from pathlib import Path

from devops_learn.bootstrap import build_platform
from devops_learn.domain.enums import AuditEventType
from devops_learn.domain.learner_profile_models import (
    CompetencyArea,
    LearnerProfile,
    ProficiencyLevel,
)
from devops_learn.domain.question_models import ClarifyingQuestion
from devops_learn.tools.approval import AutoApproveApprovalGate
from devops_learn.tools.terraform_tool import RealTerraformTool
from devops_learn.workflows.terraform_flow import TerraformOptions, run_terraform_flow
from devops_learn.workflows.ui import Ui

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "fake_terraform"


class ScriptedUi(Ui):
    def __init__(self) -> None:
        self.presented: list[str] = []

    def present(self, text: str) -> None:
        self.presented.append(text)

    def ask_choice(self, question: ClarifyingQuestion) -> str:
        return question.options[0] if question.options else "yes"

    def confirm(self, prompt: str, *, default: bool = False) -> bool:
        return True


def _platform(conn: sqlite3.Connection):
    return build_platform(
        conn, tools={"terraform": RealTerraformTool()}, approval_gate=AutoApproveApprovalGate()
    )


def _use_fake_terraform(monkeypatch, scenario: str) -> None:
    monkeypatch.setenv("PATH", f"{FIXTURES_DIR}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("FAKE_TERRAFORM_SCENARIO", scenario)


def test_successful_plan_reaches_risk_analysis_and_records_experience(
    conn: sqlite3.Connection, monkeypatch, tmp_path
) -> None:
    _use_fake_terraform(monkeypatch, "success")
    platform = _platform(conn)
    ui = ScriptedUi()
    session = run_terraform_flow(
        platform, ui, TerraformOptions(project_root=str(tmp_path), infra_root=str(tmp_path))
    )
    assert session.id is not None

    joined = "\n".join(ui.presented)
    assert "TERRAFORM PLAN" in joined
    assert "Risk: SAFE" in joined

    events = {e.event_type for e in platform.audit_service.history(session.id)}
    assert AuditEventType.TERRAFORM_PLAN_COMPLETED in events
    assert AuditEventType.DEPLOYMENT_FAILED not in events

    experience = platform.experience_tracker.summary(session.id)
    assert "Terraform" in experience
    assert "Azure" in experience


def test_plan_auth_failure_produces_credential_diagnosis(
    conn: sqlite3.Connection, monkeypatch, tmp_path
) -> None:
    _use_fake_terraform(monkeypatch, "plan_failure_with_secret")
    platform = _platform(conn)
    ui = ScriptedUi()
    session = run_terraform_flow(
        platform, ui, TerraformOptions(project_root=str(tmp_path), infra_root=str(tmp_path))
    )
    assert session.id is not None

    joined = "\n".join(ui.presented)
    assert "az login" in joined
    assert "ARM_CLIENT_SECRET" in joined
    assert "super-secret-value-123" not in joined  # redacted before ever reaching the UI

    events = {e.event_type for e in platform.audit_service.history(session.id)}
    assert AuditEventType.DEPLOYMENT_FAILED in events
    assert AuditEventType.TERRAFORM_PLAN_COMPLETED not in events


def test_generic_plan_failure_does_not_claim_an_auth_problem(
    conn: sqlite3.Connection, monkeypatch, tmp_path
) -> None:
    _use_fake_terraform(monkeypatch, "show_json_malformed")
    platform = _platform(conn)
    ui = ScriptedUi()
    run_terraform_flow(
        platform, ui, TerraformOptions(project_root=str(tmp_path), infra_root=str(tmp_path))
    )

    joined = "\n".join(ui.presented)
    assert "az login" not in joined
    assert "Diagnosis starts from the output above" in joined


def test_init_failure_stops_before_plan(
    conn: sqlite3.Connection, monkeypatch, tmp_path
) -> None:
    _use_fake_terraform(monkeypatch, "init_failure")
    platform = _platform(conn)
    ui = ScriptedUi()
    session = run_terraform_flow(
        platform, ui, TerraformOptions(project_root=str(tmp_path), infra_root=str(tmp_path))
    )
    assert session.id is not None

    events = {e.event_type for e in platform.audit_service.history(session.id)}
    assert AuditEventType.DEPLOYMENT_FAILED in events
    assert AuditEventType.TERRAFORM_PLAN_STARTED not in events


def test_beginner_learner_sees_teaching_moments(
    conn: sqlite3.Connection, monkeypatch, tmp_path
) -> None:
    _use_fake_terraform(monkeypatch, "success")
    platform = _platform(conn)
    ui = ScriptedUi()
    run_terraform_flow(
        platform, ui, TerraformOptions(project_root=str(tmp_path), infra_root=str(tmp_path))
    )
    joined = "\n".join(ui.presented)
    assert "LEARNING MOMENT: Terraform provider" in joined
    assert "LEARNING MOMENT: Terraform state" in joined


def test_learner_strong_in_terraform_sees_no_teaching_moments(
    conn: sqlite3.Connection, monkeypatch, tmp_path
) -> None:
    _use_fake_terraform(monkeypatch, "success")
    platform = _platform(conn)
    platform.learner_profile_service.save(
        LearnerProfile(
            proficiencies={CompetencyArea.TERRAFORM: ProficiencyLevel.STRONG},
            learning_focus=(),
        )
    )
    ui = ScriptedUi()
    run_terraform_flow(
        platform, ui, TerraformOptions(project_root=str(tmp_path), infra_root=str(tmp_path))
    )
    joined = "\n".join(ui.presented)
    assert "LEARNING MOMENT" not in joined


def test_mixed_actions_plan_is_classified_high_risk(
    conn: sqlite3.Connection, monkeypatch, tmp_path
) -> None:
    _use_fake_terraform(monkeypatch, "plan_mixed_actions")
    platform = _platform(conn)
    ui = ScriptedUi()
    run_terraform_flow(
        platform, ui, TerraformOptions(project_root=str(tmp_path), infra_root=str(tmp_path))
    )
    joined = "\n".join(ui.presented)
    assert "Risk: DESTRUCTIVE" in joined
