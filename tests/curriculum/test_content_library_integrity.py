from devops_learn.curriculum.content_library import build_api_platform_project
from devops_learn.domain.enums import ContentBlockKind


def test_project_has_multiple_modules_with_content() -> None:
    project = build_api_platform_project()
    assert len(project.modules) >= 5
    for module in project.modules:
        assert module.lessons, f"{module.id} has no lessons"


def test_hint_ladders_are_contiguous_and_start_at_one() -> None:
    project = build_api_platform_project()
    for module in project.modules:
        for lesson in module.lessons:
            for task in lesson.tasks:
                if not task.hints:
                    continue
                levels = [h.level for h in task.hints]
                assert levels == list(range(1, len(levels) + 1)), task.id


def test_check_question_correct_key_is_a_valid_option() -> None:
    project = build_api_platform_project()
    for module in project.modules:
        for lesson in module.lessons:
            for task in lesson.tasks:
                for block in task.content:
                    if block.kind != ContentBlockKind.CHECK_QUESTION:
                        continue
                    assert block.question is not None
                    option_keys = {o.key for o in block.question.options}
                    assert block.question.correct_key in option_keys, task.id


def test_every_task_declares_at_least_one_competency() -> None:
    project = build_api_platform_project()
    for module in project.modules:
        for lesson in module.lessons:
            for task in lesson.tasks:
                assert task.competency_codes, task.id
