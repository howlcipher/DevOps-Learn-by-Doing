"""Maps a curriculum task id to its FailureScenario.

The one explicit coupling point between curriculum content (which only knows
a task id) and the troubleshooting domain (which owns the scenario content).
"""

from __future__ import annotations

from devops_learn.curriculum.modules.module_03_troubleshoot_failure import (
    TROUBLESHOOT_CONTAINER_WONT_START_TASK_ID,
)
from devops_learn.domain.troubleshooting_models import FailureScenario
from devops_learn.troubleshooting.scenarios import build_container_wont_start_scenario

_TASK_ID_TO_SCENARIO_BUILDER = {
    TROUBLESHOOT_CONTAINER_WONT_START_TASK_ID: build_container_wont_start_scenario,
}


def scenario_for_task(task_id: str) -> FailureScenario | None:
    builder = _TASK_ID_TO_SCENARIO_BUILDER.get(task_id)
    return builder() if builder is not None else None


def is_troubleshooting_task(task_id: str) -> bool:
    return task_id in _TASK_ID_TO_SCENARIO_BUILDER
