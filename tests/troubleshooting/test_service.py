from devops_learn.tools.approval import AutoApproveApprovalGate
from devops_learn.tools.kubernetes_tool import SimulatedKubernetesTool
from devops_learn.tools.service import ToolService
from devops_learn.troubleshooting.service import TroubleshootingService


def _service() -> TroubleshootingService:
    tool_service = ToolService({"kubernetes": SimulatedKubernetesTool()}, AutoApproveApprovalGate())
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
    from devops_learn.domain.troubleshooting_models import EvidenceItem, FailureEvent

    service = _service()
    failure = FailureEvent(title="x", narrative="y", evidence=(EvidenceItem("s", "c", False),))
    diagnosis = service.diagnose(failure)
    assert diagnosis.likely_cause == "Unknown"
