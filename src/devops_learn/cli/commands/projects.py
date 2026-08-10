"""`devops-learn projects`: lists the available learning project(s)."""

from __future__ import annotations

import argparse

from devops_learn.tutor.bootstrap import Platform


def register(subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
    parser = subparsers.add_parser("projects", help="List available learning projects")
    parser.set_defaults(handler=run)


def run(args: argparse.Namespace, platform: Platform) -> None:
    project = platform.curriculum_service.project
    print(f"{project.title}  ({project.cloud.value} / {project.language.value})")
    print(project.description)
    print()
    for module in project.modules:
        print(f"- {module.title}")
