import sqlite3
from pathlib import Path

from devops_learn.bootstrap import build_platform
from devops_learn.domain.enums import (
    AuditEventType,
    CloudProviderKind,
    CostPriority,
    EnvironmentKind,
    ExplanationDepth,
    OperatingMode,
)
from devops_learn.tools.approval import AutoApproveApprovalGate
from devops_learn.workflows.analyze_flow import AnalyzeOptions, run_analysis
from devops_learn.workflows.ui import Ui
from devops_learn.domain.question_models import ClarifyingQuestion

REPO_ROOT = Path(__file__).resolve().parents[2]
API_PLATFORM = REPO_ROOT / "projects" / "api_platform"


class ScriptedUi(Ui):
    """Answers every question/confirm affirmatively without any real I/O."""

    def __init__(self) -> None:
        self.presented: list[str] = []

    def present(self, text: str) -> None:
        self.presented.append(text)

    def ask_choice(self, question: ClarifyingQuestion) -> str:
        return question.options[0] if question.options else "yes"

    def confirm(self, prompt: str, *, default: bool = False) -> bool:
        return True


def _platform(conn: sqlite3.Connection):
    return build_platform(conn, approval_gate=AutoApproveApprovalGate())


def test_full_simulation_completes_in_collaborate_mode(conn: sqlite3.Connection) -> None:
    platform = _platform(conn)
    ui = ScriptedUi()
    options = AnalyzeOptions(
        project_root=str(API_PLATFORM),
        mode=OperatingMode.COLLABORATE,
        explanation_depth=ExplanationDepth.LEARNING,
        cloud=CloudProviderKind.AZURE,
        environment=EnvironmentKind.STAGING,
        cost_priority=CostPriority.BALANCED,
        public_access=True,
        wants_kubernetes_experience=True,
    )
    session = run_analysis(platform, ui, options)
    assert session.id is not None

    events = platform.audit_service.history(session.id)
    event_types = {e.event_type for e in events}
    assert AuditEventType.PROJECT_ANALYZED in event_types
    assert AuditEventType.ARCHITECTURE_PROPOSED in event_types
    assert AuditEventType.TERRAFORM_PLAN_COMPLETED in event_types
    assert AuditEventType.DEPLOYMENT_SUCCEEDED in event_types
    assert AuditEventType.DEPLOYMENT_FAILED in event_types
    assert AuditEventType.DIAGNOSIS_PRODUCED in event_types
    assert AuditEventType.SESSION_COMPLETED in event_types

    experience = platform.experience_tracker.summary(session.id)
    assert "Terraform" in experience
    assert "Docker" in experience


def test_review_mode_never_touches_tools_or_asks_decisions(conn: sqlite3.Connection) -> None:
    platform = _platform(conn)
    ui = ScriptedUi()
    options = AnalyzeOptions(
        project_root=str(API_PLATFORM),
        mode=OperatingMode.REVIEW,
        explanation_depth=ExplanationDepth.NORMAL,
        cloud=CloudProviderKind.AZURE,
        environment=None,
        cost_priority=None,
        public_access=None,
        wants_kubernetes_experience=False,
    )
    session = run_analysis(platform, ui, options)
    assert session.id is not None

    events = platform.audit_service.history(session.id)
    event_types = {e.event_type for e in events}
    assert AuditEventType.TOOL_INVOKED not in event_types
    assert AuditEventType.QUESTION_ASKED not in event_types
    assert any("roadmap" in p.lower() for p in ui.presented)


def test_autopilot_mode_still_requires_approval_for_terraform_apply(
    conn: sqlite3.Connection,
) -> None:
    platform = _platform(conn)
    ui = ScriptedUi()
    options = AnalyzeOptions(
        project_root=str(API_PLATFORM),
        mode=OperatingMode.AUTOPILOT,
        explanation_depth=ExplanationDepth.BRIEF,
        cloud=CloudProviderKind.AZURE,
        environment=EnvironmentKind.PRODUCTION,
        cost_priority=CostPriority.BALANCED,
        public_access=True,
        wants_kubernetes_experience=False,
    )
    session = run_analysis(platform, ui, options)
    assert session.id is not None
    events = platform.audit_service.history(session.id)
    assert any(e.event_type is AuditEventType.DEPLOYMENT_SUCCEEDED for e in events)


def test_production_environment_triggers_a_higher_risk_terraform_plan(
    conn: sqlite3.Connection,
) -> None:
    platform = _platform(conn)
    ui = ScriptedUi()
    options = AnalyzeOptions(
        project_root=str(API_PLATFORM),
        mode=OperatingMode.COLLABORATE,
        explanation_depth=ExplanationDepth.NORMAL,
        cloud=CloudProviderKind.AZURE,
        environment=EnvironmentKind.PRODUCTION,
        cost_priority=CostPriority.BALANCED,
        public_access=True,
        wants_kubernetes_experience=False,
    )
    session = run_analysis(platform, ui, options)
    assert session.id is not None
    assert any("Risk: HIGH" in p for p in ui.presented)
