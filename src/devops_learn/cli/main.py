"""Entry point: `devops-learn <command>`. See docs/adr/0001-cli-first.md."""

from __future__ import annotations

import argparse
from typing import Sequence

from devops_learn.ai.anthropic_provider import AnthropicProvider
from devops_learn.cli.commands import competencies, explain, progress, projects, resume, start
from devops_learn.config.settings import load_settings
from devops_learn.learning.persistence.connection import connect
from devops_learn.tutor.bootstrap import build_platform

_COMMAND_MODULES = (start, resume, progress, projects, competencies, explain)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="devops-learn",
        description=(
            "Learn DevOps by actually doing DevOps, with an AI mentor that "
            "gradually gets out of your way."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    for module in _COMMAND_MODULES:
        module.register(subparsers)
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    settings = load_settings()
    conn = connect(settings.db_path)
    try:
        llm_provider = (
            AnthropicProvider(api_key=settings.anthropic_api_key)
            if settings.anthropic_api_key
            else None
        )
        platform = build_platform(conn, llm_provider=llm_provider)
        args.handler(args, platform)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
