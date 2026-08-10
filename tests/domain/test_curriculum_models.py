from devops_learn.domain.content import ChoiceOption, ComprehensionQuestion, ContentBlock
from devops_learn.domain.curriculum_models import Hint, LearningProject, Lesson, Module, Task
from devops_learn.domain.enums import (
    CloudProviderKind,
    CompetencyCode,
    ContentBlockKind,
    ExplanationDepth,
    LanguageTrackKind,
)


def _sample_task() -> Task:
    question = ComprehensionQuestion(
        prompt="What is the primary DevOps value of a health endpoint?",
        options=(
            ChoiceOption("A", "It encrypts requests"),
            ChoiceOption("B", "It lets systems determine application health"),
            ChoiceOption("C", "It replaces logs"),
            ChoiceOption("D", "It stores configuration"),
        ),
        correct_key="B",
        explanation_correct="Correct.",
        explanation_incorrect="Not quite — think about what a probe needs to know.",
    )
    return Task(
        id="task_health_endpoint_quiz",
        title="Understand the health endpoint",
        goal="Explain why a health endpoint matters",
        content=(
            ContentBlock(kind=ContentBlockKind.WHY, text="Systems need to know if you're up."),
            ContentBlock(
                kind=ContentBlockKind.CHECK_QUESTION,
                text="Quick check",
                question=question,
            ),
        ),
        competency_codes=(CompetencyCode.HTTP_API,),
        hints=(Hint(level=1, text="Think about what Kubernetes probes read."),),
    )


def test_task_holds_ordered_hint_ladder() -> None:
    task = Task(
        id="task_dockerfile",
        title="Write a Dockerfile",
        goal="Containerize the API",
        content=(),
        competency_codes=(CompetencyCode.DOCKER,),
        hints=(
            Hint(level=1, text="Start FROM a slim Python base image."),
            Hint(level=2, text="Copy requirements.txt before the rest of the source."),
            Hint(level=3, text="Expose the port your app listens on."),
        ),
    )
    assert [h.level for h in task.hints] == [1, 2, 3]


def test_lesson_and_module_and_project_compose() -> None:
    task = _sample_task()
    lesson = Lesson(id="lesson_health", title="The health endpoint", content=(), tasks=(task,))
    module = Module(
        id="module_01",
        title="Understand the workload",
        why_it_matters="You must understand what you operate.",
        lessons=(lesson,),
        competency_focus=(CompetencyCode.HTTP_API,),
    )
    project = LearningProject(
        id="api_platform",
        title="Production-Style API Platform",
        description="Build and operate a small API end to end.",
        cloud=CloudProviderKind.AZURE,
        language=LanguageTrackKind.PYTHON,
        modules=(module,),
    )
    assert project.modules[0].lessons[0].tasks[0].id == "task_health_endpoint_quiz"


def test_content_block_default_min_depth_is_brief() -> None:
    block = ContentBlock(kind=ContentBlockKind.WHY, text="x")
    assert block.min_depth == ExplanationDepth.BRIEF
