from devops_learn.tools import _subprocess_safety, doctor_tool
from devops_learn.tools.doctor_tool import EnvironmentDoctorTool


def test_doctor_checks_docker_runtime_and_azure_auth_without_exposing_account_data(
    monkeypatch,
) -> None:
    monkeypatch.setattr(doctor_tool.shutil, "which", lambda command: f"/tools/{command}")

    def fake_run(command, *, cwd, timeout):
        if command[1:3] == ["account", "show"]:
            return _subprocess_safety.SafeRunResult(
                0, '{"id":"subscription-id","tenantId":"tenant-id"}', "", False
            )
        return _subprocess_safety.SafeRunResult(0, "version 1.0\n", "", False)

    monkeypatch.setattr(doctor_tool._subprocess_safety, "run_safely", fake_run)

    result = EnvironmentDoctorTool().execute(
        "check", {}, dry_run=False, approval=None
    )

    checks = result.details["checks"]
    assert result.success
    assert checks["docker_daemon"]["available"]
    assert checks["azure_auth"] == {"available": True}
    assert "subscription-id" not in str(checks)
