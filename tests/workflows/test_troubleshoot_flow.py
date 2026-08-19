import sqlite3

from devops_learn.bootstrap import build_platform
from devops_learn.domain.enums import AuditEventType, ExperienceState
from devops_learn.domain.question_models import ClarifyingQuestion
from devops_learn.tools.approval import AutoApproveApprovalGate
from devops_learn.workflows.troubleshooting_flow import (
    TroubleshootingOptions,
    list_troubleshooting_scenarios,
    run_troubleshooting_flow,
)
from devops_learn.workflows.ui import Ui


class FakeUi(Ui):
    def __init__(self, choices: list[str] | None = None) -> None:
        self.presented: list[str] = []
        self.choices = list(choices or [])

    def present(self, text: str) -> None:
        self.presented.append(text)

    def ask_choice(self, question: ClarifyingQuestion) -> str:
        if self.choices:
            return self.choices.pop(0)
        return question.options[0] if question.options else "port=8081"

    def confirm(self, prompt: str, *, default: bool = False) -> bool:
        return True


def _platform(conn: sqlite3.Connection):
    return build_platform(conn, approval_gate=AutoApproveApprovalGate())


def test_list_scenarios_presents_all_options(conn: sqlite3.Connection) -> None:
    platform = _platform(conn)
    ui = FakeUi()
    list_troubleshooting_scenarios(platform, ui)
    output = "\n".join(ui.presented)
    assert "[port_conflict]" in output
    assert "[missing_config]" in output
    assert "[health_check_failure]" in output
    assert "[resource_limit]" in output


def test_troubleshooting_flow_successful_recovery(conn: sqlite3.Connection) -> None:
    platform = _platform(conn)
    ui = FakeUi()
    options = TroubleshootingOptions(
        scenario_id="port_conflict",
        hint_level=2,
        remediation_action="port=8081",
        remediation_params={"port": 8081},
        simulate=True,
    )
    evidence = run_troubleshooting_flow(platform, ui, options)

    assert evidence.resolved is True
    assert evidence.verification is not None
    assert evidence.verification.success is True
    assert evidence.mode_label == "SIMULATED / TESTED"

    # Audit events
    session = platform.session_service._session_repository.latest()
    assert session is not None
    session_id = session.id
    assert session_id is not None
    events = platform.audit_service.history(session_id)
    event_types = {e.event_type for e in events}
    assert AuditEventType.TROUBLESHOOTING_STARTED in event_types
    assert AuditEventType.TROUBLESHOOTING_REMEDIATION_ATTEMPTED in event_types
    assert AuditEventType.TROUBLESHOOTING_VERIFIED in event_types
    assert AuditEventType.TROUBLESHOOTING_COMPLETED in event_types

    # Experience tracked
    experience = platform.experience_tracker.summary(session_id)
    assert "Networking" in experience
    assert experience["Networking"][0].state == ExperienceState.DEMONSTRATED


def test_troubleshooting_flow_unsuccessful_recovery(conn: sqlite3.Connection) -> None:
    platform = _platform(conn)
    ui = FakeUi()
    options = TroubleshootingOptions(
        scenario_id="port_conflict",
        remediation_action="port=8000",
        remediation_params={"port": 8000},
        simulate=True,
    )
    evidence = run_troubleshooting_flow(platform, ui, options)

    assert evidence.resolved is False
    assert evidence.verification is not None
    assert evidence.verification.success is False

    session = platform.session_service._session_repository.latest()
    assert session is not None
    session_id = session.id
    assert session_id is not None
    events = platform.audit_service.history(session_id)
    event_types = {e.event_type for e in events}
    assert AuditEventType.TROUBLESHOOTING_FAILED in event_types


def test_troubleshooting_flow_interactive_hints_and_remediation(conn: sqlite3.Connection) -> None:
    platform = _platform(conn)
    ui = FakeUi(choices=["Level 3: Root cause explanation", "REQUIRED_CONFIG_KEY=my_key"])
    options = TroubleshootingOptions(
        scenario_id="missing_config",
        interactive=True,
        simulate=True,
    )
    evidence = run_troubleshooting_flow(platform, ui, options)
    assert evidence.resolved is True
    assert any("[HINT LEVEL 3]" in p for p in ui.presented)
