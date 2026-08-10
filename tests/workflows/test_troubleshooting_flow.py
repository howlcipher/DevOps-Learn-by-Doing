from devops_learn.curriculum.modules.module_03_troubleshoot_failure import (
    TROUBLESHOOT_CONTAINER_WONT_START_TASK_ID,
)
from devops_learn.workflows.troubleshooting_flow import (
    is_troubleshooting_task,
    scenario_for_task,
)


def test_the_module_three_task_resolves_to_the_container_scenario() -> None:
    scenario = scenario_for_task(TROUBLESHOOT_CONTAINER_WONT_START_TASK_ID)
    assert scenario is not None
    assert scenario.id == "container_wont_start"
    assert is_troubleshooting_task(TROUBLESHOOT_CONTAINER_WONT_START_TASK_ID) is True


def test_an_unrelated_task_id_resolves_to_no_scenario() -> None:
    assert scenario_for_task("task_write_dockerfile") is None
    assert is_troubleshooting_task("task_write_dockerfile") is False
