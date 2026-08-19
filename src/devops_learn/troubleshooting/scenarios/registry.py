"""Registry of available troubleshooting scenarios."""

from __future__ import annotations

from devops_learn.domain.troubleshooting_models import TroubleshootingScenario
from devops_learn.troubleshooting.scenarios.base import ScenarioHandler
from devops_learn.troubleshooting.scenarios.health_check_failure import (
    HealthCheckFailureScenarioHandler,
)
from devops_learn.troubleshooting.scenarios.missing_config import (
    MissingConfigScenarioHandler,
)
from devops_learn.troubleshooting.scenarios.port_conflict import (
    PortConflictScenarioHandler,
)
from devops_learn.troubleshooting.scenarios.resource_limit import (
    ResourceLimitScenarioHandler,
)

_HANDLERS: tuple[ScenarioHandler, ...] = (
    PortConflictScenarioHandler(),
    MissingConfigScenarioHandler(),
    HealthCheckFailureScenarioHandler(),
    ResourceLimitScenarioHandler(),
)


class ScenarioRegistry:
    def __init__(self, handlers: tuple[ScenarioHandler, ...] | None = None) -> None:
        self._handlers = handlers or _HANDLERS
        self._by_id = {h.definition.scenario_id: h for h in self._handlers}

    def list_scenarios(self) -> tuple[TroubleshootingScenario, ...]:
        return tuple(h.definition for h in self._handlers)

    def get_handler(self, scenario_id: str) -> ScenarioHandler:
        handler = self._by_id.get(scenario_id)
        if handler is None:
            valid = ", ".join(self._by_id.keys())
            raise KeyError(
                f"Unknown troubleshooting scenario '{scenario_id}'. Available scenarios: {valid}"
            )
        return handler

    def get_scenario(self, scenario_id: str) -> TroubleshootingScenario:
        return self.get_handler(scenario_id).definition
