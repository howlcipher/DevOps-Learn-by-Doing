"""`devops-learn explain <topic>`: freeform explanation outside any active session."""

from __future__ import annotations

import argparse

from devops_learn.bootstrap import Platform
from devops_learn.domain.enums import ExplanationDepth


def register(subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
    parser = subparsers.add_parser("explain", help="Ask the platform to explain a topic")
    parser.add_argument("topic", nargs="+", help="Topic to explain")
    parser.add_argument(
        "--depth", choices=[d.name.lower() for d in ExplanationDepth], default="normal"
    )
    parser.set_defaults(handler=run)


def run(args: argparse.Namespace, platform: Platform) -> None:
    topic = " ".join(args.topic)
    depth = ExplanationDepth[args.depth.upper()]
    explanation = platform.llm.explain_topic(topic, depth=depth)
    print(explanation.title.upper())
    print()
    print(explanation.body)
