import json
from datetime import datetime, timezone

from devops_learn.domain.enums import AuditEventType, ExecutionMode, ExplanationDepth
from devops_learn.domain.explanation_models import Explanation
from devops_learn.domain.security_models import PolicyResult, SecurityReport
from devops_learn.domain.enums import SecurityGateDecision
from devops_learn.explanations.service import ExplanationService
from devops_learn.learning.persistence.repositories.audit_repository import AuditRepository
from devops_learn.audit.service import AuditService
from devops_learn.security.normalization import normalize_trivy
from devops_learn.security.reporting import write_report

FAKE_SECRET = "demo-only-fixture-9f31b7-not-a-real-token"


def _secret_finding():
    return normalize_trivy(
        {
            "Results": [
                {
                    "Target": "fixture.py",
                    "Secrets": [
                        {
                            "RuleID": "demo",
                            "Title": "Synthetic secret",
                            "Match": FAKE_SECRET,
                            "Severity": "CRITICAL",
                        }
                    ],
                }
            ]
        }
    )[0]


def test_fake_secret_cannot_reach_explanation_report_or_audit(
    seeded_session, conn, tmp_path
) -> None:
    finding = _secret_finding()
    explanation = ExplanationService().render(
        Explanation(action=finding.title, why=finding.evidence),
        mode=ExecutionMode.COLLABORATIVE,
        depth=ExplanationDepth.DEEP,
    )
    assert FAKE_SECRET not in explanation

    report_path = tmp_path / "report.json"
    write_report(
        SecurityReport(
            (finding,), PolicyResult(SecurityGateDecision.BLOCK, ("secret",)), {}, None, "fixture"
        ),
        report_path,
    )
    assert FAKE_SECRET not in report_path.read_text()

    audit = AuditService(AuditRepository(conn))
    audit.record(
        session_id=seeded_session,
        event_type=AuditEventType.SECURITY_SCAN_COMPLETED,
        occurred_at=datetime.now(timezone.utc),
        summary="Synthetic scan",
        payload={"Match": FAKE_SECRET},
    )
    assert FAKE_SECRET not in json.dumps(audit.history(seeded_session)[0].payload)
