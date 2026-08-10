import argparse

import pytest

from devops_learn.cli.commands import projects
from devops_learn.tutor.bootstrap import Platform


def test_prints_the_project_header_and_every_module_title(
    platform: Platform, capsys: pytest.CaptureFixture[str]
) -> None:
    projects.run(argparse.Namespace(), platform)
    output = capsys.readouterr().out

    project = platform.curriculum_service.project
    assert project.title in output
    assert project.cloud.value in output
    assert project.language.value in output
    assert project.description in output
    for module in project.modules:
        assert f"- {module.title}" in output
