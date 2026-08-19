"""Unit tests for troubleshooting scenario handlers and registry."""

from typing import Any
import pytest

from devops_learn.domain.troubleshooting_models import RemediationAttempt
from devops_learn.tools.approval import AutoApproveApprovalGate
from devops_learn.tools.docker_tool import SimulatedDockerTool
from devops_learn.tools.service import ToolService
from devops_learn.troubleshooting.scenarios.base import ScenarioContext
from devops_learn.troubleshooting.scenarios.health_check_failure import (
    HealthCheckFailureScenarioHandler,
)
from devops_learn.troubleshooting.scenarios.missing_config import (
    MissingConfigScenarioHandler,
)
from devops_learn.troubleshooting.scenarios.port_conflict import (
    PortConflictScenarioHandler,
)
from devops_learn.troubleshooting.scenarios.registry import ScenarioRegistry
from devops_learn.troubleshooting.scenarios.resource_limit import (
    ResourceLimitScenarioHandler,
)


def _make_context(handler: Any) -> ScenarioContext:
    tool_service = ToolService({"docker": SimulatedDockerTool()}, AutoApproveApprovalGate())
    return ScenarioContext(
        scenario=handler.definition,
        is_live=False,
        project_root=".",
        tool_service=tool_service,
    )


def test_scenario_registry_contains_all_core_scenarios() -> None:
    registry = ScenarioRegistry()
    scenarios = registry.list_scenarios()
    ids = {s.scenario_id for s in scenarios}
    assert "port_conflict" in ids
    assert "missing_config" in ids
    assert "health_check_failure" in ids
    assert "resource_limit" in ids
    assert len(scenarios) == 4


def test_scenario_registry_raises_for_unknown_scenario() -> None:
    registry = ScenarioRegistry()
    with pytest.raises(KeyError) as exc_info:
        registry.get_handler("nonexistent_scenario")
    assert "Available scenarios:" in str(exc_info.value)


def test_port_conflict_lifecycle() -> None:
    handler = PortConflictScenarioHandler()
    ctx = _make_context(handler)

    # 1. Setup & Inject
    obs = handler.setup_and_inject(ctx)
    assert any(
        "port is already allocated" in o.content or "address already in use" in o.content
        for o in obs
    )
    assert any(o.is_error for o in obs)

    # 2. Bad remediation (port 8000 still conflicting)
    bad_attempt = RemediationAttempt("port_conflict", "port=8000", {"port": 8000})
    bad_obs = handler.remediate(ctx, bad_attempt)
    assert bad_obs[0].is_error
    bad_ver = handler.verify(ctx, bad_attempt)
    assert not bad_ver.success

    # 3. Good remediation (port 8081)
    good_attempt = RemediationAttempt("port_conflict", "port=8081", {"port": 8081})
    good_obs = handler.remediate(ctx, good_attempt)
    assert not good_obs[0].is_error
    good_ver = handler.verify(ctx, good_attempt)
    assert good_ver.success
    assert "8081" in good_ver.summary

    # 4. Cleanup
    handler.cleanup(ctx)


def test_missing_config_lifecycle() -> None:
    handler = MissingConfigScenarioHandler()
    ctx = _make_context(handler)

    # 1. Setup & Inject
    obs = handler.setup_and_inject(ctx)
    assert any("REQUIRED_CONFIG_KEY" in o.content for o in obs)

    # 2. Bad remediation
    bad_attempt = RemediationAttempt("missing_config", "wrong_param=1", {})
    bad_obs = handler.remediate(ctx, bad_attempt)
    assert bad_obs[0].is_error
    bad_ver = handler.verify(ctx, bad_attempt)
    assert not bad_ver.success

    # 3. Good remediation
    good_attempt = RemediationAttempt(
        "missing_config",
        "REQUIRED_CONFIG_KEY=val",
        {"REQUIRED_CONFIG_KEY": "valid_123"},
    )
    good_obs = handler.remediate(ctx, good_attempt)
    assert not good_obs[0].is_error
    good_ver = handler.verify(ctx, good_attempt)
    assert good_ver.success

    # 4. Cleanup
    handler.cleanup(ctx)


def test_health_check_failure_lifecycle() -> None:
    handler = HealthCheckFailureScenarioHandler()
    ctx = _make_context(handler)

    # 1. Setup & Inject
    obs = handler.setup_and_inject(ctx)
    assert any("503" in o.content for o in obs)

    # 2. Bad remediation
    bad_attempt = RemediationAttempt(
        "health_check_failure",
        "status=unhealthy",
        {"dependency_status": "unhealthy"},
    )
    bad_obs = handler.remediate(ctx, bad_attempt)
    assert bad_obs[0].is_error
    bad_ver = handler.verify(ctx, bad_attempt)
    assert not bad_ver.success

    # 3. Good remediation
    good_attempt = RemediationAttempt(
        "health_check_failure",
        "dependency_status=healthy",
        {"dependency_status": "healthy"},
    )
    good_obs = handler.remediate(ctx, good_attempt)
    assert not good_obs[0].is_error
    good_ver = handler.verify(ctx, good_attempt)
    assert good_ver.success

    # 4. Cleanup
    handler.cleanup(ctx)


def test_resource_limit_lifecycle() -> None:
    handler = ResourceLimitScenarioHandler()
    ctx = _make_context(handler)

    # 1. Setup & Inject
    obs = handler.setup_and_inject(ctx)
    assert any(o.exit_code == 137 for o in obs)

    # 2. Bad remediation (too small memory limit: 8m)
    bad_attempt = RemediationAttempt("resource_limit", "memory_limit=8m", {"memory_limit": "8m"})
    bad_obs = handler.remediate(ctx, bad_attempt)
    assert bad_obs[0].is_error
    bad_ver = handler.verify(ctx, bad_attempt)
    assert not bad_ver.success

    # 3. Good remediation (64m)
    good_attempt = RemediationAttempt(
        "resource_limit", "memory_limit=64m", {"memory_limit": "64m"}
    )
    good_obs = handler.remediate(ctx, good_attempt)
    assert not good_obs[0].is_error
    good_ver = handler.verify(ctx, good_attempt)
    assert good_ver.success
    assert "64" in good_ver.summary

    # 4. Cleanup
    handler.cleanup(ctx)
