import pytest

from devops_learn.curriculum.service import CurriculumError, CurriculumService


def test_first_module_is_understand_workload() -> None:
    service = CurriculumService()
    assert service.first_module().id == "module_01_understand_workload"


def test_next_module_walks_in_order_and_ends_with_none() -> None:
    service = CurriculumService()
    module_ids = [m.id for m in service.project.modules]
    current = module_ids[0]
    seen = [current]
    while True:
        nxt = service.next_module(current)
        if nxt is None:
            break
        seen.append(nxt.id)
        current = nxt.id
    assert seen == module_ids


def test_unknown_task_id_raises_curriculum_error() -> None:
    service = CurriculumService()
    with pytest.raises(CurriculumError):
        service.task("does_not_exist")


def test_task_lookup_and_parents_are_consistent() -> None:
    service = CurriculumService()
    task = service.task("task_write_dockerfile")
    module, lesson = service.parents_of_task(task.id)
    assert module.id == "module_02_containerize"
    assert task in lesson.tasks
