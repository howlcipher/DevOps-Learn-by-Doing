from devops_learn.domain.enums import FindingCategory, FindingSeverity
from devops_learn.security.normalization import normalize_trivy
from devops_learn.security.reporting import write_report
from devops_learn.domain.security_models import PolicyResult, SecurityReport
from devops_learn.domain.enums import SecurityGateDecision

FAKE_SECRET = "DEVSECOPS_DEMO_ONLY_NOT_A_CREDENTIAL_9f31b7"


def _document() -> dict:
    return {
        "Results": [
            {
                "Target": "infra/main.tf",
                "Type": "terraform",
                "Vulnerabilities": [
                    {
                        "VulnerabilityID": "CVE-2026-0001",
                        "PkgName": "demo",
                        "InstalledVersion": "1.0",
                        "FixedVersion": "1.1",
                        "Severity": "HIGH",
                        "Title": "demo vulnerability",
                    }
                ],
                "Misconfigurations": [
                    {
                        "ID": "AVD-AZU-0001",
                        "Title": "Public SSH ingress",
                        "Description": "opens a port",
                        "Severity": "HIGH",
                        "CauseMetadata": {"StartLine": 42},
                    }
                ],
                "Secrets": [
                    {
                        "RuleID": "generic-api-key",
                        "Title": "Synthetic secret",
                        "Severity": "CRITICAL",
                        "Match": FAKE_SECRET,
                        "StartLine": 3,
                    }
                ],
            }
        ]
    }


def test_normalizes_vulnerability_iac_and_secret_without_match() -> None:
    findings = normalize_trivy(_document())
    assert {finding.category for finding in findings} == {
        FindingCategory.DEPENDENCY,
        FindingCategory.NETWORK,
        FindingCategory.SECRET,
    }
    secret = next(finding for finding in findings if finding.category is FindingCategory.SECRET)
    assert secret.severity is FindingSeverity.CRITICAL
    assert FAKE_SECRET not in str(secret)
    assert "REDACTED" in (secret.evidence or "")


def test_incomplete_and_unknown_trivy_json_is_safe() -> None:
    assert (
        normalize_trivy({"Results": [{"Target": "x", "Secrets": [{}]}]})[0].category
        is FindingCategory.SECRET
    )
    assert normalize_trivy({"Results": "not-a-list"}) == ()


def test_secret_never_survives_report_serialization(tmp_path) -> None:
    finding = next(
        item for item in normalize_trivy(_document()) if item.category is FindingCategory.SECRET
    )
    report = SecurityReport(
        (finding,), PolicyResult(SecurityGateDecision.BLOCK, ("secret",)), {}, None, "fixture"
    )
    path = tmp_path / "security-report.json"
    write_report(report, path)
    assert FAKE_SECRET not in path.read_text()
