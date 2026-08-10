"""`devops-learn explain <topic>`: freeform explanation outside any active session."""

from __future__ import annotations

import argparse

from devops_learn.domain.enums import AssistanceLevel, ExplanationDepth
from devops_learn.tutor.bootstrap import Platform


def register(subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
    parser = subparsers.add_parser("explain", help="Ask the tutor to explain a topic")
    parser.add_argument("topic", nargs="+", help="Topic to explain")
    parser.set_defaults(handler=run)


def run(args: argparse.Namespace, platform: Platform) -> None:
    topic = " ".join(args.topic)
    profile = platform.profile_repository.latest()
    level = profile.assistance_level if profile is not None else AssistanceLevel.GUIDED
    depth = profile.explanation_depth if profile is not None else ExplanationDepth.NORMAL

    explanation = platform.llm.explain_topic(topic, level=level, depth=depth)
    print(explanation.title.upper())
    print()
    print(explanation.body)
