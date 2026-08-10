"""Module 4: infrastructure as code, up through interpreting a Terraform plan."""

from __future__ import annotations

from devops_learn.domain.content import ContentBlock, MenuOption, PredictionPrompt
from devops_learn.domain.curriculum_models import Hint, Lesson, Module, Task
from devops_learn.domain.enums import CompetencyCode, ContentBlockKind, ExplanationDepth

TERRAFORM_PLAN_TASK_ID = "task_terraform_plan"


def build_module() -> Module:
    task = Task(
        id=TERRAFORM_PLAN_TASK_ID,
        title="Interpret a Terraform plan",
        goal="Read a terraform plan output and explain what it will change before applying it.",
        content=(
            ContentBlock(
                kind=ContentBlockKind.WHY,
                text=(
                    "Terraform lets you describe infrastructure as code instead of clicking "
                    "through a console, so changes are reviewable, repeatable, and versioned "
                    "the same way application code is."
                ),
                always_include=True,
            ),
            ContentBlock(
                kind=ContentBlockKind.WHAT,
                text=(
                    "A provider block configures which cloud API Terraform talks to; a "
                    "resource block declares one thing that should exist; terraform plan "
                    "computes the difference between your configuration and reality without "
                    "changing anything."
                ),
            ),
            ContentBlock(
                kind=ContentBlockKind.HOW,
                text=(
                    "The lifecycle you will practice is: write configuration, terraform "
                    "validate to catch syntax and type errors, then terraform plan to see "
                    "what would change. See templates/terraform/main.tf.reference."
                ),
                min_depth=ExplanationDepth.NORMAL,
            ),
            ContentBlock(
                kind=ContentBlockKind.PITFALL,
                text=(
                    "A plan showing any Destroy count against a resource holding state you "
                    "care about (like a database) is worth stopping and re-reading before "
                    "you ever apply it."
                ),
                min_depth=ExplanationDepth.LEARNING,
            ),
            ContentBlock(
                kind=ContentBlockKind.NEXT_STEP_MENU,
                text="Options:",
                always_include=True,
                menu_options=(
                    MenuOption("A", "Run terraform validate"),
                    MenuOption("B", "Run terraform plan"),
                    MenuOption("C", "Explain resource blocks"),
                    MenuOption("D", "Show me the reference configuration"),
                ),
            ),
        ),
        competency_codes=(CompetencyCode.TERRAFORM,),
        hints=(
            Hint(level=1, text="Count how many resource blocks the configuration declares."),
            Hint(
                level=2,
                text="A fresh plan against no existing state creates every declared resource.",
            ),
        ),
        full_explanation=ContentBlock(
            kind=ContentBlockKind.DETAIL,
            text=(
                "With no prior state, terraform plan will show Create for every resource "
                "block in the configuration and Modify/Destroy as zero, since nothing exists "
                "yet for Terraform to compare against."
            ),
        ),
        prediction=PredictionPrompt(
            prompt=(
                "Before running it: how many resources do you expect terraform plan to "
                "report as Create, given the reference configuration has not been applied "
                "before?"
            ),
            outcome_summary=(
                "The plan creates every resource declared in the configuration, since "
                "Terraform has no existing state to compare against yet."
            ),
        ),
    )

    lesson = Lesson(
        id="lesson_terraform_plan",
        title="Infrastructure as code: plan before apply",
        content=(),
        tasks=(task,),
    )

    return Module(
        id="module_04_terraform_plan",
        title="Infrastructure as code",
        why_it_matters=(
            "Cloud resources cost money and can be destructive to change; reading a plan "
            "correctly before applying it is a foundational safety habit."
        ),
        lessons=(lesson,),
        competency_focus=(CompetencyCode.TERRAFORM, CompetencyCode.TERRAFORM_STATE),
    )
