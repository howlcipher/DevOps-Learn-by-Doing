from devops_learn.curriculum.service import CurriculumService


def test_next_task_walks_across_every_module_to_the_end() -> None:
    service = CurriculumService()
    project = service.project

    module = project.modules[0]
    lesson = module.lessons[0]
    task = lesson.tasks[0]

    visited_module_ids = [module.id]
    steps = 0
    while True:
        result = service.next_task(module.id, lesson.id, task.id if task else None)
        steps += 1
        assert steps < 100, "navigation looped or never terminated"
        if result is None:
            break
        module, lesson, task = result
        if module.id != visited_module_ids[-1]:
            visited_module_ids.append(module.id)

    assert visited_module_ids == [m.id for m in project.modules]


def test_next_task_within_a_lesson_advances_task_before_lesson() -> None:
    service = CurriculumService()
    module = service.module("module_01_understand_workload")
    lesson = module.lessons[0]
    # module_01's single lesson has exactly one task, so this should fall through
    # to "next lesson" / "next module" rather than staying within the lesson.
    result = service.next_task(module.id, lesson.id, lesson.tasks[0].id)
    assert result is not None
    next_module, next_lesson, next_task = result
    assert next_module.id == "module_02_containerize"


def test_next_task_handles_a_content_only_lesson_with_no_tasks() -> None:
    service = CurriculumService()
    module = service.module("module_05_kubernetes_overview")
    lesson = module.lessons[0]
    assert lesson.tasks == ()
    result = service.next_task(module.id, lesson.id, None)
    assert result is None  # module_05 is the last module
