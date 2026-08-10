import argparse
import sqlite3
from pathlib import Path
from typing import Any

import pytest

from devops_learn.ai.anthropic_provider import AnthropicProvider
from devops_learn.ai.mock_provider import MockLLMProvider
from devops_learn.cli import main as main_module
from devops_learn.cli.main import build_parser, main
from devops_learn.tutor.bootstrap import Platform


def test_all_six_commands_are_registered() -> None:
    parser = build_parser()
    subparsers_action = next(
        a for a in parser._actions if a.dest == "command"  # type: ignore[attr-defined]
    )
    assert set(subparsers_action.choices) == {
        "start",
        "resume",
        "progress",
        "projects",
        "competencies",
        "explain",
    }


def test_start_defaults_to_simulation_mode() -> None:
    parser = build_parser()
    args = parser.parse_args(["start"])
    assert args.simulation is True


def test_explain_requires_a_topic() -> None:
    parser = build_parser()
    args = parser.parse_args(["explain", "readiness", "probes"])
    assert args.topic == ["readiness", "probes"]


@pytest.fixture()
def db_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "state" / "learning.db"
    monkeypatch.setenv("DEVOPS_LEARN_DB_PATH", str(path))
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    return path


def _spy_on_build_platform(monkeypatch: pytest.MonkeyPatch) -> list[Any]:
    providers: list[Any] = []
    real = main_module.build_platform

    def spy(conn: sqlite3.Connection, **kwargs: Any) -> Platform:
        providers.append(kwargs.get("llm_provider"))
        return real(conn, **kwargs)

    monkeypatch.setattr(main_module, "build_platform", spy)
    return providers


def test_main_creates_the_database_and_runs_the_parsed_handler(
    db_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    main(["projects"])

    assert db_path.exists()
    assert "Production-Style API Platform" in capsys.readouterr().out


def test_main_defaults_to_the_mock_provider_without_credentials(
    db_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    providers = _spy_on_build_platform(monkeypatch)

    main(["projects"])

    assert providers == [None]


def test_main_uses_the_anthropic_provider_when_an_api_key_is_set(
    db_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    providers = _spy_on_build_platform(monkeypatch)

    main(["projects"])

    assert isinstance(providers[0], AnthropicProvider)


def test_main_closes_the_connection_when_the_handler_fails(
    db_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    connections: list[sqlite3.Connection] = []
    real_connect = main_module.connect

    def spy_connect(path: Path) -> sqlite3.Connection:
        conn = real_connect(path)
        connections.append(conn)
        return conn

    def boom(args: argparse.Namespace, platform: Platform) -> None:
        raise RuntimeError("handler failed")

    monkeypatch.setattr(main_module, "connect", spy_connect)
    monkeypatch.setattr("devops_learn.cli.commands.projects.run", boom)

    with pytest.raises(RuntimeError, match="handler failed"):
        main(["projects"])

    assert len(connections) == 1
    with pytest.raises(sqlite3.ProgrammingError):
        connections[0].execute("SELECT 1")


def test_build_platform_falls_back_to_the_mock_provider(tmp_path: Path) -> None:
    conn = main_module.connect(tmp_path / "learning.db")
    try:
        platform = main_module.build_platform(conn)
    finally:
        conn.close()

    assert isinstance(platform.llm, MockLLMProvider)
