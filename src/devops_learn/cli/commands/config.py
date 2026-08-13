"""`devops-learn config`: display configuration settings."""

from __future__ import annotations

import argparse

from devops_learn.bootstrap import Platform
from devops_learn.config.settings import load_settings


def register(subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
    parser = subparsers.add_parser("config", help="Manage configuration")
    subparsers_config = parser.add_subparsers(dest="config_command", required=True)
    show_parser = subparsers_config.add_parser("show", help="Show current configuration")
    show_parser.set_defaults(handler=run_show)


def run_show(args: argparse.Namespace, platform: Platform) -> None:
    settings = load_settings()
    has_key = bool(settings.anthropic_api_key)

    print("DEVOPS-LEARN CONFIGURATION")
    print(f"{'Database path':<25} {settings.db_path}")
    print(f"{'AI Provider':<25} {settings.ai_provider}")
    print(f"{'Anthropic credential':<25} {'Configured' if has_key else 'Not configured'}")
