"""`devops-learn init <path>`: project intake and learner profile setup.

The init command inspects a repository, asks only the questions that cannot be
safely inferred, and records the learner's skill profile so later explanations
can target the right depth for the right topic.
"""

from __future__ import annotations

import argparse

from devops_learn.bootstrap import Platform
from devops_learn.cli.terminal_ui import TerminalUi
from devops_learn.domain.analysis_models import ProjectAssessment
from devops_learn.domain.enums import CloudProviderKind, CostPriority, EnvironmentKind
from devops_learn.domain.learner_profile_models import (
    CompetencyArea,
    LearnerProfile,
    ProficiencyLevel,
)

_ALL_AREAS = sorted(CompetencyArea, key=lambda a: a.value)


def register(subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
    parser = subparsers.add_parser(
        "init", help="Inspect a project and set up your learner profile"
    )
    parser.add_argument("path", help="Path to the project to initialize")
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Skip interactive questions and print a summary only",
    )
    parser.set_defaults(handler=run)


def run(args: argparse.Namespace, platform: Platform) -> None:
    ui = TerminalUi()
    assessment = platform.analyzer.analyze(args.path)
    ui.present(_render_assessment(assessment))

    profile = platform.learner_profile_service.load()
    if args.non_interactive:
        _show_summary(ui, assessment, profile, EnvironmentKind.DEV, CostPriority.BALANCED)
        return

    cloud = _ask_cloud(ui)
    environment = _ask_environment(ui)
    cost_priority = _ask_cost_priority(ui)
    focus = _ask_learning_focus(ui)
    profile = _update_profile(profile, focus, ui)
    platform.learner_profile_service.save(profile)

    _show_summary(ui, assessment, profile, environment, cost_priority, cloud=cloud)


def _render_assessment(assessment: ProjectAssessment) -> str:
    from devops_learn.workflows import presenters

    return presenters.render_assessment(assessment)


def _ask_cloud(ui: TerminalUi) -> CloudProviderKind:
    from devops_learn.domain.question_models import ClarifyingQuestion

    question = ClarifyingQuestion(
        id="cloud",
        category="cloud",
        prompt="Which cloud provider do you want to target?",
        options=tuple(c.value for c in CloudProviderKind),
    )
    return CloudProviderKind(ui.ask_choice(question))


def _ask_environment(ui: TerminalUi) -> EnvironmentKind:
    from devops_learn.domain.question_models import ClarifyingQuestion

    question = ClarifyingQuestion(
        id="environment",
        category="environment",
        prompt="Which environment is this for?",
        options=("Development", "Production-like", "Production"),
    )
    answer = ui.ask_choice(question).lower()
    if "production-like" in answer:
        return EnvironmentKind.STAGING
    if "production" in answer:
        return EnvironmentKind.PRODUCTION
    return EnvironmentKind.DEV


def _ask_cost_priority(ui: TerminalUi) -> CostPriority:
    from devops_learn.domain.question_models import ClarifyingQuestion

    question = ClarifyingQuestion(
        id="cost_priority",
        category="cost",
        prompt="Should we optimize primarily for cost or availability?",
        options=("Lowest cost", "Balanced", "Highest availability"),
    )
    answer = ui.ask_choice(question).lower()
    if "cost" in answer:
        return CostPriority.LOWEST_COST
    if "availability" in answer:
        return CostPriority.HIGHEST_AVAILABILITY
    return CostPriority.BALANCED


def _ask_learning_focus(ui: TerminalUi) -> list[CompetencyArea]:
    lines = [
        "",
        "Which areas do you want to strengthen during this project?",
        "Enter comma-separated numbers (e.g. 1,4,7), or press Enter to skip.",
    ]
    for i, area in enumerate(_ALL_AREAS, start=1):
        lines.append(f"  {i}. {area.value}")
    print("\n".join(lines))
    raw = input("> ").strip()
    if not raw:
        return []
    focus: list[CompetencyArea] = []
    for token in raw.split(","):
        token = token.strip()
        if token.isdigit():
            idx = int(token) - 1
            if 0 <= idx < len(_ALL_AREAS):
                focus.append(_ALL_AREAS[idx])
    return focus


def _update_profile(
    profile: LearnerProfile, focus: list[CompetencyArea], ui: TerminalUi
) -> LearnerProfile:
    proficiencies = dict(profile.proficiencies)
    for area in focus:
        if area not in proficiencies:
            proficiencies[area] = ProficiencyLevel.BEGINNER

    current_focus = list(profile.learning_focus)
    for area in focus:
        if area not in current_focus:
            current_focus.append(area)

    if ui.confirm("Would you like to rate any other skill areas now?", default=False):
        for area in _ALL_AREAS:
            level = _ask_proficiency(ui, area)
            proficiencies[area] = level

    return LearnerProfile(
        proficiencies=proficiencies, learning_focus=tuple(current_focus)
    )


def _ask_proficiency(ui: TerminalUi, area: CompetencyArea) -> ProficiencyLevel:
    from devops_learn.domain.question_models import ClarifyingQuestion

    question = ClarifyingQuestion(
        id=f"proficiency_{area.value}",
        category="learning_profile",
        prompt=f"What is your current level for {area.value}?",
        options=tuple(level.value for level in ProficiencyLevel),
    )
    return ProficiencyLevel(ui.ask_choice(question))


def _show_summary(
    ui: TerminalUi,
    assessment: ProjectAssessment,
    profile: LearnerProfile,
    environment: EnvironmentKind,
    cost_priority: CostPriority,
    cloud: CloudProviderKind | None = None,
) -> None:
    lines = ["INIT SUMMARY", ""]
    lines.append(f"Project: {assessment.root_path}")
    lines.append(f"Detected: {assessment.application_type}")
    if cloud is not None:
        lines.append(f"Target cloud: {cloud.value}")
    lines.append(f"Environment: {environment.value}")
    lines.append(f"Cost priority: {cost_priority.value}")
    if profile.learning_focus:
        lines.append(
            "Learning focus: " + ", ".join(a.value for a in profile.learning_focus)
        )
    else:
        lines.append("Learning focus: none set")
    lines.append("")
    lines.append(
        "Run 'devops-learn analyze <path> --mode collaborative --depth learning' "
        "to start the workflow."
    )
    ui.present("\n".join(lines))
