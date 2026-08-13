"""`devops-learn ai-test`: real AI provider smoke test."""

from __future__ import annotations
import argparse
from devops_learn.bootstrap import Platform
from devops_learn.cli.terminal_ui import TerminalUi
from devops_learn.domain.enums import ExplanationDepth


def register(subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
    parser = subparsers.add_parser(
        "ai-test", help="Smoke test the live AI provider configuration"
    )
    parser.set_defaults(handler=run)


def run(args: argparse.Namespace, platform: Platform) -> None:
    ui = TerminalUi()
    ui.present("DEVOPS LEARN // AI SMOKE TEST")
    ui.present("")

    provider_name = platform.llm.__class__.__name__

    if provider_name == "MockLLMProvider":
        ui.present("FAIL: Current provider is MockLLMProvider.")
        ui.present("To test the live AI, configure DEVOPS_LEARN_AI_PROVIDER=anthropic")
        ui.present("and ANTHROPIC_API_KEY.")
        return

    ui.present(f"Provider: {provider_name}")
    ui.present("Sending a small explanation request...")

    try:
        explanation = platform.llm.explain_topic(
            "HTTP Health Check",
            depth=ExplanationDepth.BRIEF,
        )
        ui.present("")
        ui.present("SUCCESS: AI explanation received.")
        ui.present(f"Title: {explanation.title}")
        ui.present(f"Body:  {explanation.body}")
    except Exception as e:
        ui.present("")
        ui.present(f"FAIL: {str(e)}")
