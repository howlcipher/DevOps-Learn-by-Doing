"""CLI command integration tests for `devops-learn troubleshoot`."""

import pytest
from devops_learn.cli.main import build_parser, main


def test_troubleshoot_parser_registration() -> None:
    parser = build_parser()
    args = parser.parse_args(["troubleshoot", "list"])
    assert args.command == "troubleshoot"
    assert args.troubleshoot_command == "list"

    args = parser.parse_args(
        ["troubleshoot", "run", "port_conflict", "--hint-level", "2", "--remediation", "port=8081"]
    )
    assert args.command == "troubleshoot"
    assert args.troubleshoot_command == "run"
    assert args.scenario == "port_conflict"
    assert args.hint_level == 2
    assert args.remediation == "port=8081"


def test_troubleshoot_cli_execution_success(capsys: pytest.CaptureFixture[str]) -> None:
    main(["troubleshoot", "run", "port_conflict", "--remediation", "port=8081", "--simulate"])
    captured = capsys.readouterr()
    assert "TROUBLESHOOTING: Port Binding Collision" in captured.out
    assert "[PASS] Port collision resolved." in captured.out


def test_troubleshoot_cli_execution_failure(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["troubleshoot", "run", "port_conflict", "--remediation", "port=8000", "--simulate"])
    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "[FAIL]" in captured.out


def test_troubleshoot_cli_list(capsys: pytest.CaptureFixture[str]) -> None:
    main(["troubleshoot", "list"])
    captured = capsys.readouterr()
    assert "AVAILABLE TROUBLESHOOTING SCENARIOS" in captured.out
    assert "[port_conflict]" in captured.out
    assert "[missing_config]" in captured.out
