import os
import sqlite3
from pathlib import Path

from devops_learn.bootstrap import build_platform
from devops_learn.deployment.candidate import DeploymentCandidate, sha256_file
from devops_learn.domain.enums import (
    CloudProviderKind,
    CostPriority,
    EnvironmentKind,
    ExecutionMode,
    ExplanationDepth,
    SecurityGateDecision,
)
from devops_learn.domain.question_models import ClarifyingQuestion
from devops_learn.tools.approval import AutoApproveApprovalGate
from devops_learn.tools.terraform_tool import RealTerraformTool, terraform_config_digest
from devops_learn.workflows.deploy_flow import _plan_and_gate
from devops_learn.workflows.ui import Ui

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "fake_terraform"


class ScriptedUi(Ui):
    def __init__(self, confirmations: list[bool]) -> None:
        self.confirmations = confirmations
        self.presented: list[str] = []

    def present(self, text: str) -> None:
        self.presented.append(text)

    def ask_choice(self, question: ClarifyingQuestion) -> str:
        return question.options[0] if question.options else "yes"

    def confirm(self, prompt: str, *, default: bool = False) -> bool:
        return self.confirmations.pop(0)


def _platform(conn: sqlite3.Connection):
    return build_platform(
        conn, tools={"terraform": RealTerraformTool()}, approval_gate=AutoApproveApprovalGate()
    )


def _candidate(infra: Path, report: Path, decision: SecurityGateDecision) -> DeploymentCandidate:
    return DeploymentCandidate(
        source_revision="source-a",
        project_path="projects/api_platform",
        cloud="azure",
        environment="learning",
        terraform_config_digest=terraform_config_digest(infra),
        security_report_path=str(report),
        security_report_digest=sha256_file(report),
        security_decision=decision.value,
    )


def _session_id(platform, infra: Path) -> int:
    session = platform.session_service.start(
        project_root=str(infra),
        mode=ExecutionMode.COLLABORATIVE,
        explanation_depth=ExplanationDepth.NORMAL,
        cloud=CloudProviderKind.AZURE,
        environment=EnvironmentKind.DEV,
        cost_priority=CostPriority.LOWEST_COST,
        simulation_mode=False,
    )
    assert session.id is not None
    return session.id


def test_blocked_security_evidence_stops_before_cloud_action(
    conn: sqlite3.Connection, monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("PATH", f"{FIXTURES_DIR}{os.pathsep}{os.environ['PATH']}")
    report = tmp_path / "security.json"
    report.write_text('{"decision":"block"}\n')
    platform = _platform(conn)
    ui = ScriptedUi([])

    result = _plan_and_gate(
        platform,
        ui,
        tmp_path,
        _candidate(tmp_path, report, SecurityGateDecision.BLOCK),
        {"deploy_application": False, "location": "eastus"},
        _session_id(platform, tmp_path),
    )

    assert result is None
    assert "SECURITY BLOCK" in "\n".join(ui.presented)
    assert ui.confirmations == []


def test_required_security_and_cloud_approval_bind_the_saved_plan(
    conn: sqlite3.Connection, monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("PATH", f"{FIXTURES_DIR}{os.pathsep}{os.environ['PATH']}")
    report = tmp_path / "security.json"
    report.write_text('{"decision":"require_approval"}\n')
    platform = _platform(conn)
    ui = ScriptedUi([True, True])

    result = _plan_and_gate(
        platform,
        ui,
        tmp_path,
        _candidate(tmp_path, report, SecurityGateDecision.REQUIRE_APPROVAL),
        {"deploy_application": False, "location": "eastus"},
        _session_id(platform, tmp_path),
    )

    assert result is not None
    assert result.human_approvals == ("security", "cloud_action")
    assert result.terraform_plan_path is not None
    assert Path(result.terraform_plan_path).is_file()
