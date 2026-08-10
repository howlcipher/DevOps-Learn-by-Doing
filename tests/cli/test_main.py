from devops_learn.cli.main import build_parser


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
