"""Module 3: an intentional failure and guided troubleshooting.

The interactive evidence-gathering itself is not authored as ContentBlocks. It
is driven by troubleshooting/service.py against the FailureScenario built in
troubleshooting/scenarios.py, orchestrated by workflows/troubleshooting_flow.py.
Task.id here is the handoff key that flow maps to a scenario id.
"""

from __future__ import annotations

from devops_learn.domain.content import ContentBlock
from devops_learn.domain.curriculum_models import Lesson, Module, Task
from devops_learn.domain.enums import CompetencyCode, ContentBlockKind, ExplanationDepth

TROUBLESHOOT_CONTAINER_WONT_START_TASK_ID = "troubleshoot_container_wont_start"


def build_module() -> Module:
    task = Task(
        id=TROUBLESHOOT_CONTAINER_WONT_START_TASK_ID,
        title="Diagnose why the container will not start",
        goal="Reach a correct root-cause diagnosis using only the evidence you choose to inspect.",
        content=(
            ContentBlock(
                kind=ContentBlockKind.WHY,
                text=(
                    "Production systems fail. The skill that separates a platform engineer "
                    "from someone who can only follow a happy path is knowing where to look "
                    "first, and how to reason from evidence to a diagnosis."
                ),
                always_include=True,
            ),
            ContentBlock(
                kind=ContentBlockKind.WHAT,
                text="The API container will not start.",
            ),
            ContentBlock(
                kind=ContentBlockKind.DETAIL,
                text=(
                    "You will be offered a menu of things you could inspect. Not everything "
                    "you inspect will be relevant; picking well is part of the skill."
                ),
                min_depth=ExplanationDepth.NORMAL,
            ),
        ),
        competency_codes=(CompetencyCode.TROUBLESHOOTING, CompetencyCode.DOCKER),
    )

    lesson = Lesson(
        id="lesson_troubleshoot_failure",
        title="Diagnose a failing deployment",
        content=(),
        tasks=(task,),
    )

    return Module(
        id="module_03_troubleshoot_failure",
        title="Troubleshoot a failure",
        why_it_matters=(
            "Building something is only half the job; operating it when it breaks is the "
            "other half, and it is the half most learning resources skip."
        ),
        lessons=(lesson,),
        competency_focus=(CompetencyCode.TROUBLESHOOTING,),
    )
