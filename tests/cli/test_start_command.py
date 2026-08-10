"""Onboarding prompt behaviour for `devops-learn start`."""

import argparse
import io
import sqlite3

import pytest

from devops_learn.cli.commands import start
from devops_learn.tutor.bootstrap import build_platform


@pytest.mark.parametrize("stdin_text", ["", "1\n1\n", "1\nquit\n"])
def test_onboarding_ends_cleanly_without_creating_a_profile(
    conn: sqlite3.Connection,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    stdin_text: str,
) -> None:
    """End of input or 'quit' must not traceback, and must leave no half-set-up learner."""
    monkeypatch.setattr("sys.stdin", io.StringIO(stdin_text))
    platform = build_platform(conn)

    start.run(argparse.Namespace(simulation=True), platform)

    assert "Setup cancelled" in capsys.readouterr().out
    assert platform.profile_repository.latest() is None
