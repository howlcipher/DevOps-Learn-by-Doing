"""`devops-learn profile`: view and update the learner skill profile.

The profile records which DevOps concepts the learner already understands and
which they want to strengthen. The platform uses this to spend explanation time
where gaps exist rather than treating every topic the same.
"""

from __future__ import annotations

import argparse

from devops_learn.bootstrap import Platform
from devops_learn.domain.learner_profile_models import CompetencyArea


ALL_AREAS = sorted(CompetencyArea, key=lambda a: a.value)


def register(subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
    parser = subparsers.add_parser(
        "profile",
        help="Show or update your learner skill profile",
    )
    parser.add_argument(
        "--set",
        action="append",
        dest="set_entries",
        metavar="area=level",
        help="Set a competency area to a level, e.g. docker=strong terraform=beginner",
    )
    parser.add_argument(
        "--focus",
        action="append",
        dest="focus_areas",
        metavar="area",
        help="Mark an area as a learning focus, e.g. --focus terraform --focus azure",
    )
    parser.set_defaults(handler=run)


def run(args: argparse.Namespace, platform: Platform) -> None:
    service = platform.learner_profile_service
    profile = service.load()

    if args.set_entries or args.focus_areas:
        proficiencies = dict(profile.proficiencies)
        if args.set_entries:
            for entry in args.set_entries:
                area_text, level_text = _parse_assignment(entry)
                proficiencies[service.parse_area(area_text)] = service.parse_level(level_text)
        focus = list(profile.learning_focus)
        if args.focus_areas:
            for area_text in args.focus_areas:
                area = service.parse_area(area_text)
                if area not in focus:
                    focus.append(area)
        profile = service.save(
            profile.__class__(proficiencies=proficiencies, learning_focus=tuple(focus))
        )

    lines = ["LEARNER PROFILE", ""]
    for area in ALL_AREAS:
        level = profile.level(area)
        marker = " *" if area in profile.learning_focus else ""
        lines.append(f"{area.value}: {level.value}{marker}")
    if profile.learning_focus:
        lines.append("")
        lines.append("Learning focus: " + ", ".join(a.value for a in profile.learning_focus))
    print("\n".join(lines))


def _parse_assignment(entry: str) -> tuple[str, str]:
    if "=" not in entry:
        raise argparse.ArgumentTypeError(
            f"Profile entry must be area=level, got: {entry!r}"
        )
    area_text, level_text = entry.split("=", 1)
    return area_text.strip(), level_text.strip()
