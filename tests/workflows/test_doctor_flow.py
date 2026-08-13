from devops_learn.workflows.doctor_flow import DoctorCheck, DoctorReport, render_doctor_report


def test_doctor_report_exposes_capability_specific_readiness() -> None:
    report = DoctorReport(
        checks=(
            DoctorCheck("Python", True, "3.11.9"),
            DoctorCheck("Docker", True, "29.0"),
            DoctorCheck("Docker daemon", True, "29.0"),
            DoctorCheck("Azure CLI", True, "2.88"),
            DoctorCheck("Azure auth", False),
            DoctorCheck("Trivy", True, "0.70"),
            DoctorCheck("Conftest", True, "0.69"),
        ),
        local_workflow_ready=True,
        security_workflow_ready=True,
        terraform_planning_ready=False,
        azure_deployment_ready=False,
        ai_provider="Mock",
        ai_mode="OFFLINE",
        db_writable=True,
    )

    rendered = render_doctor_report(report)

    assert "Docker daemon  PASS" in rendered
    assert "Local workflow:     YES" in rendered
    assert "Security workflow:  YES" in rendered
    assert "Terraform planning: NO" in rendered
    assert "Azure deployment:   NO" in rendered
    assert "Authenticate Azure using `az login`." in rendered
