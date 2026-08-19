from devops_learn.domain.troubleshooting_models import (
    EvidenceItem,
    FailureEvent,
    HintLevel,
    RemediationAttempt,
)
from devops_learn.tools.approval import AutoApproveApprovalGate
from devops_learn.tools.docker_tool import SimulatedDockerTool
from devops_learn.tools.kubernetes_tool import SimulatedKubernetesTool
from devops_learn.tools.service import ToolService
from devops_learn.troubleshooting.service import TroubleshootingService


def _service() -> TroubleshootingService:
    tool_service = ToolService(
        {
            "kubernetes": SimulatedKubernetesTool(),
            "docker": SimulatedDockerTool(),
        },
        AutoApproveApprovalGate(),
    )
    return TroubleshootingService(tool_service)


def test_gather_evidence_collects_multiple_sources_before_any_diagnosis() -> None:
    failure = _service().gather_evidence()
    assert len(failure.evidence) >= 3
    assert any(item.is_relevant for item in failure.evidence)


def test_diagnosis_is_derived_from_relevant_evidence_only() -> None:
    service = _service()
    failure = service.gather_evidence()
    diagnosis = service.diagnose(failure)
    assert "readiness probe" in diagnosis.likely_cause.lower()
    assert diagnosis.recommended_fix
    assert diagnosis.learning_moment is not None


def test_diagnosis_without_relevant_evidence_is_honest_about_uncertainty() -> None:
    service = _service()
    failure = FailureEvent(title="x", narrative="y", evidence=(EvidenceItem("s", "c", False),))
    diagnosis = service.diagnose(failure)
    assert diagnosis.likely_cause == "Unknown"


def test_list_and_get_scenarios() -> None:
    service = _service()
    scenarios = service.list_scenarios()
    assert len(scenarios) == 4
    scenario = service.get_scenario("port_conflict")
    assert scenario.scenario_id == "port_conflict"
    assert "EADDRINUSE" in scenario.title


def test_progressive_hints_levels() -> None:
    service = _service()
    h0 = service.get_hint("port_conflict", HintLevel.EVIDENCE)
    h1 = service.get_hint("port_conflict", HintLevel.INSPECTION)
    h2 = service.get_hint("port_conflict", HintLevel.SUBSYSTEM)
    h3 = service.get_hint("port_conflict", HintLevel.ROOT_CAUSE)
    h4 = service.get_hint("port_conflict", HintLevel.REMEDIATION)

    assert "Observation:" in h0
    assert "Inspection:" in h1
    assert "Subsystem:" in h2
    assert "Root Cause:" in h3
    assert "Remediation:" in h4


def test_service_start_session_and_interpret() -> None:
    service = _service()
    session, ctx, obs = service.start_session("port_conflict", is_live=False)
    assert session.scenario.scenario_id == "port_conflict"
    assert len(obs) >= 2

    interpretations = service.interpret(obs)
    assert len(interpretations) >= 1
    assert "Port bind conflict" in interpretations[0].observation_summary

    attempt = RemediationAttempt("port_conflict", "port=8081", {"port": 8081})
    rem_obs = service.remediate(session, ctx, attempt)
    assert not rem_obs[0].is_error

    ver = service.verify(session, ctx, attempt)
    assert ver.success
    service.cleanup(session, ctx)
