"""Entry point: `devops-learn <command>`. See docs/adr/0001-cli-first.md."""

from __future__ import annotations

import argparse
from typing import Sequence

from devops_learn.ai.anthropic_provider import AnthropicProvider
from devops_learn.bootstrap import build_platform
from devops_learn.cli.commands import analyze, explain, history, review
from devops_learn.config.settings import load_settings
from devops_learn.learning.persistence.connection import connect

_COMMAND_MODULES = (analyze, review, history, explain)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="devops-learn",
        description=(
            "AI-powered, explainable DevOps platform: assess a project, recommend and explain "
            "an architecture, build it with human approval, and validate the result."
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
