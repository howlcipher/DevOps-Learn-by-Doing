"""Every id lookup fails loudly rather than returning None or a wrong node."""

import dataclasses

import pytest

from devops_learn.curriculum.service import CurriculumError, CurriculumService


@pytest.fixture()
def service() -> CurriculumService:
    return CurriculumService()


def test_unknown_module_id_raises(service: CurriculumService) -> None:
    with pytest.raises(CurriculumError, match="Unknown module id"):
        service.module("module_99")


def test_unknown_lesson_id_raises(service: CurriculumService) -> None:
    with pytest.raises(CurriculumError, match="Unknown lesson id"):
        service.lesson("lesson_99")


def test_unknown_lesson_id_raises_when_asking_for_its_module(service: CurriculumService) -> None:
    with pytest.raises(CurriculumError, match="Unknown lesson id"):
        service.module_for_lesson("lesson_99")


def test_unknown_task_id_raises_when_asking_for_its_parents(service: CurriculumService) -> None:
    with pytest.raises(CurriculumError, match="Unknown task id"):
        service.parents_of_task("task_99")


def test_module_for_lesson_agrees_with_the_module_lesson_list(service: CurriculumService) -> None:
    module = service.module_for_lesson("lesson_kubernetes_overview")
    assert module.id == "module_05_kubernetes_overview"
    assert any(lesson.id == "lesson_kubernetes_overview" for lesson in module.lessons)


def test_next_task_stays_inside_a_lesson_that_has_more_tasks(service: CurriculumService) -> None:
    """Authored content currently has one task per lesson, so this uses a project
    with a two-task lesson to pin the within-lesson step down."""
    module = service.module("module_02_containerize")
    lesson = module.lessons[0]
    second_task = dataclasses.replace(lesson.tasks[0], id="task_write_dockerfile_part_two")
    lesson = dataclasses.replace(lesson, tasks=(lesson.tasks[0], second_task))
    module = dataclasses.replace(module, lessons=(lesson,))
    multi_task_service = CurriculumService(
        dataclasses.replace(service.project, modules=(module,))
    )

    result = multi_task_service.next_task(module.id, lesson.id, lesson.tasks[0].id)

    assert result is not None
    next_module, next_lesson, next_task = result
    assert (next_module.id, next_lesson.id) == (module.id, lesson.id)
    assert next_task is not None
    assert next_task.id == "task_write_dockerfile_part_two"


def test_next_task_moves_to_the_next_lesson_before_the_next_module(
    service: CurriculumService,
) -> None:
    """Authored modules currently hold one lesson each, so this uses a project with a
    two-lesson module to pin the lesson step down."""
    module = service.module("module_02_containerize")
    first_lesson = module.lessons[0]
    second_lesson = dataclasses.replace(first_lesson, id="lesson_containerize_part_two")
    module = dataclasses.replace(module, lessons=(first_lesson, second_lesson))
    two_lesson_service = CurriculumService(
        dataclasses.replace(service.project, modules=(module,))
    )

    result = two_lesson_service.next_task(
        module.id, first_lesson.id, first_lesson.tasks[0].id
    )

    assert result is not None
    next_module, next_lesson, next_task = result
    assert next_module.id == module.id
    assert next_lesson.id == "lesson_containerize_part_two"
    assert next_task is not None


def test_next_task_from_the_final_task_of_the_final_module_ends_the_project(
    service: CurriculumService,
) -> None:
    last_module = service.project.modules[-1]
    last_lesson = last_module.lessons[-1]
    last_task_id = last_lesson.tasks[-1].id if last_lesson.tasks else None

    assert service.next_task(last_module.id, last_lesson.id, last_task_id) is None
