"""Module 2: containerize the application with Docker."""

from __future__ import annotations

from devops_learn.domain.content import ContentBlock, MenuOption, PredictionPrompt
from devops_learn.domain.curriculum_models import Challenge, Hint, Lesson, Module, Task
from devops_learn.domain.enums import CompetencyCode, ContentBlockKind, ExplanationDepth


def build_module() -> Module:
    task = Task(
        id="task_write_dockerfile",
        title="Containerize the application",
        goal="Create a Dockerfile that builds and runs the API as a portable image.",
        content=(
            ContentBlock(
                kind=ContentBlockKind.WHY,
                text=(
                    "Containers give us a repeatable runtime environment that can move "
                    "between your computer, CI, and Kubernetes unchanged."
                ),
                always_include=True,
            ),
            ContentBlock(
                kind=ContentBlockKind.WHAT,
                text=(
                    "An image is the packaged artifact. A container is a running instance "
                    "of that image."
                ),
            ),
            ContentBlock(
                kind=ContentBlockKind.HOW,
                text=(
                    "A minimal Dockerfile: FROM a slim Python base, COPY requirements.txt, "
                    "RUN pip install, COPY the rest of the source, EXPOSE the app port, then "
                    "CMD to start it. See templates/docker/Dockerfile.reference for a worked "
                    "example."
                ),
                min_depth=ExplanationDepth.NORMAL,
            ),
            ContentBlock(
                kind=ContentBlockKind.PITFALL,
                text=(
                    "Copying the full source before installing dependencies invalidates "
                    "Docker's layer cache on every code change, forcing a full reinstall "
                    "each build."
                ),
                min_depth=ExplanationDepth.LEARNING,
            ),
            ContentBlock(
                kind=ContentBlockKind.DETAIL,
                text=(
                    "Prefer a non-root user and a pinned base image tag for basic container "
                    "security; both matter more once this image reaches a registry other "
                    "people pull from."
                ),
                min_depth=ExplanationDepth.DEEP,
            ),
            ContentBlock(
                kind=ContentBlockKind.NEXT_STEP_MENU,
                text="Options:",
                always_include=True,
                menu_options=(
                    MenuOption("A", "I'll write it"),
                    MenuOption("B", "Give me a hint"),
                    MenuOption("C", "Explain Dockerfile instructions"),
                    MenuOption("D", "Show me a partial example"),
                    MenuOption("E", "Generate it and explain every step"),
                ),
            ),
        ),
        competency_codes=(CompetencyCode.DOCKER,),
        hints=(
            Hint(level=1, text="Start FROM a slim official Python base image."),
            Hint(
                level=2,
                text=(
                    "COPY requirements.txt and install dependencies before copying the "
                    "rest of the source."
                ),
            ),
            Hint(level=3, text="EXPOSE the port your app listens on and set CMD to run it."),
        ),
        full_explanation=ContentBlock(
            kind=ContentBlockKind.DETAIL,
            text=(
                "FROM python:3.11-slim, WORKDIR /app, COPY requirements.txt then RUN pip "
                "install --no-cache-dir -r requirements.txt, COPY . ., EXPOSE 8000, CMD "
                '["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"].'
            ),
        ),
        prediction=PredictionPrompt(
            prompt=(
                "Before you build: what do you expect happens if you swap the order and "
                "COPY the entire source before COPY requirements.txt?"
            ),
            outcome_summary=(
                "Reordering invalidates Docker's layer cache: every code change, even a "
                "one-line edit, now forces a full dependency reinstall instead of reusing "
                "the cached install layer."
            ),
        ),
        challenge=Challenge(
            id="challenge_multistage_build",
            title="Multi-stage build",
            prompt="Rewrite the Dockerfile as a multi-stage build to shrink the final image.",
        ),
    )

    lesson = Lesson(
        id="lesson_containerize",
        title="Containerize the application",
        content=(),
        tasks=(task,),
    )

    return Module(
        id="module_02_containerize",
        title="Containerize the application",
        why_it_matters=(
            "Every later stage, CI, Kubernetes, rollback, operates on the image you build "
            "here, not on your source tree directly."
        ),
        lessons=(lesson,),
        competency_focus=(CompetencyCode.DOCKER,),
    )
