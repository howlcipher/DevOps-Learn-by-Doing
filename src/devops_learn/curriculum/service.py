"""Read-only access to the curriculum content graph, plus rendering."""

from __future__ import annotations

from devops_learn.curriculum.content_library import build_api_platform_project
from devops_learn.curriculum.renderer import ArrangedContent, render_content
from devops_learn.domain.curriculum_models import LearningProject, Lesson, Module, Task
from devops_learn.domain.enums import AssistanceLevel, ExplanationDepth


class CurriculumError(Exception):
    """Raised when a module/lesson/task id does not exist in the loaded project."""


class CurriculumService:
    def __init__(self, project: LearningProject | None = None) -> None:
        self._project = project or build_api_platform_project()
        self._modules_by_id: dict[str, Module] = {}
        self._lesson_parent: dict[str, Module] = {}
        self._lessons_by_id: dict[str, Lesson] = {}
        self._task_parent: dict[str, tuple[Module, Lesson]] = {}
        self._tasks_by_id: dict[str, Task] = {}
        for module in self._project.modules:
            self._modules_by_id[module.id] = module
            for lesson in module.lessons:
                self._lessons_by_id[lesson.id] = lesson
                self._lesson_parent[lesson.id] = module
                for task in lesson.tasks:
                    self._tasks_by_id[task.id] = task
                    self._task_parent[task.id] = (module, lesson)

    @property
    def project(self) -> LearningProject:
        return self._project

    def module(self, module_id: str) -> Module:
        try:
            return self._modules_by_id[module_id]
        except KeyError as exc:
            raise CurriculumError(f"Unknown module id: {module_id}") from exc

    def lesson(self, lesson_id: str) -> Lesson:
        try:
            return self._lessons_by_id[lesson_id]
        except KeyError as exc:
            raise CurriculumError(f"Unknown lesson id: {lesson_id}") from exc

    def task(self, task_id: str) -> Task:
        try:
            return self._tasks_by_id[task_id]
        except KeyError as exc:
            raise CurriculumError(f"Unknown task id: {task_id}") from exc

    def module_for_lesson(self, lesson_id: str) -> Module:
        try:
            return self._lesson_parent[lesson_id]
        except KeyError as exc:
            raise CurriculumError(f"Unknown lesson id: {lesson_id}") from exc

    def parents_of_task(self, task_id: str) -> tuple[Module, Lesson]:
        try:
            return self._task_parent[task_id]
        except KeyError as exc:
            raise CurriculumError(f"Unknown task id: {task_id}") from exc

    def first_module(self) -> Module:
        return self._project.modules[0]

    def next_module(self, current_module_id: str) -> Module | None:
        module_ids = [m.id for m in self._project.modules]
        index = module_ids.index(current_module_id)
        if index + 1 >= len(module_ids):
            return None
        return self._project.modules[index + 1]

    def render_task_content(
        self, task: Task, level: AssistanceLevel, depth: ExplanationDepth
    ) -> ArrangedContent:
        return render_content(task.content, level, depth)

    def next_task(
        self, module_id: str, lesson_id: str, task_id: str | None
    ) -> tuple[Module, Lesson, Task | None] | None:
        """Walks task -> lesson -> module in order. Returns None past the last module.

        task_id may be None for a content-only lesson (e.g. module_05, which has
        no tasks); that case skips straight to "move to the next lesson".
        """
        module = self.module(module_id)
        lesson = self.lesson(lesson_id)

        if task_id is not None:
            task_ids = [t.id for t in lesson.tasks]
            index = task_ids.index(task_id)
            if index + 1 < len(task_ids):
                return module, lesson, lesson.tasks[index + 1]

        lesson_ids = [lesson_.id for lesson_ in module.lessons]
        lesson_index = lesson_ids.index(lesson_id)
        if lesson_index + 1 < len(lesson_ids):
            next_lesson = module.lessons[lesson_index + 1]
            next_task_ = next_lesson.tasks[0] if next_lesson.tasks else None
            return module, next_lesson, next_task_

        next_module = self.next_module(module_id)
        if next_module is None:
            return None
        first_lesson = next_module.lessons[0]
        first_task = first_lesson.tasks[0] if first_lesson.tasks else None
        return next_module, first_lesson, first_task
