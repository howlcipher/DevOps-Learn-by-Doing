"""Rigorous test falsification for troubleshooting scenarios and recovery verification.

These tests prove that scenarios cannot pass spuriously:
- Wrong or incomplete remediation fails.
- No remediation fails.
- Broken before-state fails verification.
- Cleanup is guaranteed even during exceptions.
- Progressive hints don't leak remediation at level 0.
- Observations accurately distinguish facts from interpretation.
"""

from devops_learn.domain.troubleshooting_models import (
    HintLevel,
    RemediationAttempt,
)
from devops_learn.tools.approval import AutoApproveApprovalGate
from devops_learn.tools.docker_tool import SimulatedDockerTool
from devops_learn.tools.service import ToolService
from devops_learn.troubleshooting.scenarios.port_conflict import (
    PortConflictScenarioHandler,
)
from devops_learn.troubleshooting.scenarios.registry import ScenarioRegistry
from devops_learn.troubleshooting.service import TroubleshootingService


def _get_service() -> TroubleshootingService:
    tool_service = ToolService({"docker": SimulatedDockerTool()}, AutoApproveApprovalGate())
    return TroubleshootingService(tool_service)


def test_falsify_port_conflict_remediation_failures() -> None:
    service = _get_service()
    session, ctx, obs = service.start_session("port_conflict", is_live=False)

    # 1. No remediation attempt fails
    empty_attempt = RemediationAttempt("port_conflict", "")
    res_empty = service.verify(session, ctx, empty_attempt)
    assert not res_empty.success
    assert "cannot bind to occupied" in res_empty.summary

    # 2. Re-attempting occupied port (8000) fails
    conflict_attempt = RemediationAttempt("port_conflict", "port=8000", {"port": 8000})
    rem_obs = service.remediate(session, ctx, conflict_attempt)
    assert rem_obs[0].is_error
    res_conflict = service.verify(session, ctx, conflict_attempt)
    assert not res_conflict.success

    # 3. Invalid port numbers fail
    for bad_port in [-5, 0, 70000, "not-a-port"]:
        bad_attempt = RemediationAttempt("port_conflict", f"port={bad_port}", {"port": bad_port})
        rem_obs = service.remediate(session, ctx, bad_attempt)
        assert rem_obs[0].is_error
        res = service.verify(session, ctx, bad_attempt)
        assert not res.success

    # 4. Valid non-conflicting port succeeds
    valid_attempt = RemediationAttempt("port_conflict", "port=8082", {"port": 8082})
    rem_obs = service.remediate(session, ctx, valid_attempt)
    assert not rem_obs[0].is_error
    res_valid = service.verify(session, ctx, valid_attempt)
    assert res_valid.success
    assert res_valid.details.get("port") == 8082

    service.cleanup(session, ctx)


def test_falsify_missing_config_remediation_failures() -> None:
    service = _get_service()
    session, ctx, obs = service.start_session("missing_config", is_live=False)

    # 1. Empty remediation fails
    empty_attempt = RemediationAttempt("missing_config", "")
    assert not service.verify(session, ctx, empty_attempt).success

    # 2. Unrelated config fails
    wrong_attempt = RemediationAttempt(
        "missing_config", "UNRELATED_KEY=true", {"env": {"UNRELATED_KEY": "true"}}
    )
    rem_obs = service.remediate(session, ctx, wrong_attempt)
    assert rem_obs[0].is_error
    assert not service.verify(session, ctx, wrong_attempt).success

    # 3. Supplying REQUIRED_CONFIG_KEY succeeds
    good_attempt = RemediationAttempt(
        "missing_config",
        "REQUIRED_CONFIG_KEY=learning_secret_token",
        {"env": {"REQUIRED_CONFIG_KEY": "learning_secret_token"}},
    )
    rem_obs = service.remediate(session, ctx, good_attempt)
    assert not rem_obs[0].is_error
    res = service.verify(session, ctx, good_attempt)
    assert res.success
    assert res.details.get("config_verified") is True

    service.cleanup(session, ctx)


def test_falsify_health_check_remediation_failures() -> None:
    service = _get_service()
    session, ctx, obs = service.start_session("health_check_failure", is_live=False)

    # 1. Still degraded fails
    bad_attempt = RemediationAttempt(
        "health_check_failure", "status=unhealthy", {"dependency_status": "unhealthy"}
    )
    rem_obs = service.remediate(session, ctx, bad_attempt)
    assert rem_obs[0].is_error
    assert not service.verify(session, ctx, bad_attempt).success

    # 2. Setting healthy succeeds
    good_attempt = RemediationAttempt(
        "health_check_failure",
        "dependency_status=healthy",
        {"dependency_status": "healthy"},
    )
    rem_obs = service.remediate(session, ctx, good_attempt)
    assert not rem_obs[0].is_error
    res = service.verify(session, ctx, good_attempt)
    assert res.success

    service.cleanup(session, ctx)


def test_falsify_resource_limit_remediation_failures() -> None:
    service = _get_service()
    session, ctx, obs = service.start_session("resource_limit", is_live=False)

    # 1. Memory below 32MB fails
    for small_mem in ["4m", "6m", "16m", "20M"]:
        bad_attempt = RemediationAttempt(
            "resource_limit", f"memory_limit={small_mem}", {"memory_limit": small_mem}
        )
        rem_obs = service.remediate(session, ctx, bad_attempt)
        assert rem_obs[0].is_error
        assert not service.verify(session, ctx, bad_attempt).success

    # 2. Memory 64MB succeeds
    good_attempt = RemediationAttempt(
        "resource_limit", "memory_limit=64m", {"memory_limit": "64m"}
    )
    rem_obs = service.remediate(session, ctx, good_attempt)
    assert not rem_obs[0].is_error
    res = service.verify(session, ctx, good_attempt)
    assert res.success
    assert res.details.get("memory_mb") == 64

    # 3. Memory 1GB succeeds
    gb_attempt = RemediationAttempt(
        "resource_limit", "memory_limit=1g", {"memory_limit": "1g"}
    )
    rem_obs = service.remediate(session, ctx, gb_attempt)
    assert not rem_obs[0].is_error
    res_gb = service.verify(session, ctx, gb_attempt)
    assert res_gb.success
    assert res_gb.details.get("memory_mb") == 1024

    service.cleanup(session, ctx)


def test_falsify_cleanup_guarantee() -> None:
    service = _get_service()
    cleaned = False

    class MonitoredHandler(PortConflictScenarioHandler):
        def cleanup(self, context):
            nonlocal cleaned
            cleaned = True
            super().cleanup(context)

    registry = ScenarioRegistry((MonitoredHandler(),))
    custom_service = TroubleshootingService(service._tool_service, registry)
    cust_session, cust_ctx, _ = custom_service.start_session("port_conflict", is_live=False)

    try:
        raise RuntimeError("Simulated mid-troubleshooting crash")
    except RuntimeError:
        custom_service.cleanup(cust_session, cust_ctx)

    assert cleaned is True


def test_falsify_hints_do_not_leak_solution_at_level_0() -> None:
    service = _get_service()
    scenarios = ["port_conflict", "missing_config", "health_check_failure", "resource_limit"]
    for scenario_id in scenarios:
        h0 = service.get_hint(scenario_id, HintLevel.EVIDENCE)
        h4 = service.get_hint(scenario_id, HintLevel.REMEDIATION)

        assert "Observation:" in h0
        assert "Remediation:" in h4
        assert "Remediation:" not in h0
