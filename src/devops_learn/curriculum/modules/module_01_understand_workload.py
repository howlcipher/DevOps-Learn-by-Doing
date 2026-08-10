"""Module 1: understand the demo workload before touching any infrastructure."""

from __future__ import annotations

from devops_learn.domain.content import (
    ChoiceOption,
    ComprehensionQuestion,
    ContentBlock,
    MenuOption,
)
from devops_learn.domain.curriculum_models import Hint, Lesson, Module, Task
from devops_learn.domain.enums import CompetencyCode, ContentBlockKind, ExplanationDepth


def build_module() -> Module:
    health_question = ComprehensionQuestion(
        prompt="What is the primary DevOps value of a health endpoint?",
        options=(
            ChoiceOption("A", "It encrypts requests"),
            ChoiceOption("B", "It lets systems determine application health"),
            ChoiceOption("C", "It replaces logs"),
            ChoiceOption("D", "It stores configuration"),
        ),
        correct_key="B",
        explanation_correct=(
            "Correct. Later, Docker and Kubernetes will use this concept when deciding "
            "whether the application is functioning correctly."
        ),
        explanation_incorrect=(
            "Not quite. Think about what an external system needs to know before it can "
            "safely route traffic to, or restart, your application."
        ),
    )

    task = Task(
        id="task_understand_health_and_info",
        title="Understand the workload's endpoints",
        goal="Explain what /health and /info are for before touching any infrastructure.",
        content=(
            ContentBlock(
                kind=ContentBlockKind.WHY,
                text=(
                    "A platform engineer does not need to be the application's primary "
                    "developer, but must understand what the workload needs in order to "
                    "build, deploy, monitor, and troubleshoot its platform."
                ),
                always_include=True,
            ),
            ContentBlock(
                kind=ContentBlockKind.WHAT,
                text="The application exposes GET /health and GET /info.",
            ),
            ContentBlock(
                kind=ContentBlockKind.HOW,
                text=(
                    '/health returns a small JSON body such as {"status": "ok"} with no '
                    "dependencies checked in V1. /info returns non-secret metadata: service "
                    "name, version, and environment, read from environment variables."
                ),
                min_depth=ExplanationDepth.NORMAL,
            ),
            ContentBlock(
                kind=ContentBlockKind.ANALOGY,
                text=(
                    "Think of /health like a pulse check taken before every other diagnosis: "
                    "cheap, fast, and asked constantly by things you never see."
                ),
                min_depth=ExplanationDepth.LEARNING,
            ),
            ContentBlock(
                kind=ContentBlockKind.DETAIL,
                text=(
                    "Kubernetes liveness and readiness probes will call /health directly; an "
                    "endpoint that is slow or has side effects becomes a platform risk, not "
                    "just an application concern."
                ),
                min_depth=ExplanationDepth.DEEP,
            ),
            ContentBlock(
                kind=ContentBlockKind.CHECK_QUESTION,
                text="Quick check",
                question=health_question,
            ),
            ContentBlock(
                kind=ContentBlockKind.NEXT_STEP_MENU,
                text="Would you like to:",
                always_include=True,
                menu_options=(
                    MenuOption("A", "Inspect the Python application"),
                    MenuOption("B", "Run it"),
                    MenuOption("C", "Explain the code"),
                    MenuOption("D", "Show me the entire project roadmap"),
                ),
            ),
        ),
        competency_codes=(CompetencyCode.PYTHON_BASICS, CompetencyCode.HTTP_API),
        hints=(
            Hint(
                level=1,
                text="Think about what happens the moment before traffic reaches a new instance.",
            ),
            Hint(
                level=2,
                text=(
                    "A load balancer or Kubernetes probe cannot read application logs before "
                    "deciding whether to send traffic."
                ),
            ),
        ),
        full_explanation=ContentBlock(
            kind=ContentBlockKind.DETAIL,
            text=(
                "A health endpoint gives any external system, a load balancer, an "
                "orchestrator, a monitoring tool, a cheap and structured way to ask 'are you "
                "okay?' without inspecting logs or guessing from timeouts."
            ),
        ),
    )

    lesson = Lesson(
        id="lesson_understand_workload",
        title="Understand the workload",
        content=(),
        tasks=(task,),
    )

    return Module(
        id="module_01_understand_workload",
        title="Understand the workload",
        why_it_matters=(
            "You cannot safely build, deploy, monitor, or troubleshoot a platform for code "
            "you do not understand at least at the level of its contracts."
        ),
        lessons=(lesson,),
        competency_focus=(CompetencyCode.PYTHON_BASICS, CompetencyCode.HTTP_API),
    )
