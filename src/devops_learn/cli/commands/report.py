"""`devops-learn report`: evidence report generation."""

from __future__ import annotations

import argparse
import json

from devops_learn.bootstrap import Platform
from devops_learn.domain.enums import AuditEventType


def register(subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
    parser = subparsers.add_parser(
        "report", help="Generate an engineering evidence report"
    )
    parser.add_argument(
        "--latest", action="store_true", help="Report on the latest session"
    )
    parser.add_argument(
        "--session", type=int, help="Session ID to report (defaults to latest)"
    )
    parser.add_argument(
        "--format",
        choices=["markdown", "json"],
        default="markdown",
        help="Output format",
    )
    parser.add_argument("--output", help="Output file path (default: stdout)")
    parser.set_defaults(handler=run)


def run(args: argparse.Namespace, platform: Platform) -> None:
    session = platform.session_service.latest()
    if not session:
        print("No sessions found.")
        return
    assert session.id is not None

    events = platform.audit_service.history(session.id)
    experiences = platform.experience_tracker.summary(session.id)

    event_types = {e.event_type for e in events}

    sections: dict[str, list[str]] = {
        "REAL PASS": [],
        "REAL FAIL": [],
        "SIMULATED": [],
        "NOT EXECUTED": [],
    }

    if session.simulation_mode:
        sections["SIMULATED"].extend(
            ["Python tests", "Docker build", "Terraform validate", "Security scan"]
        )
        sections["NOT EXECUTED"].append("Azure deployment")
    else:
        if any(
            e.event_type == AuditEventType.TOOL_INVOKED
            and isinstance(e.payload, dict)
            and e.payload.get("tool") == "python"
            for e in events
        ):
            sections["REAL PASS"].append("Python tests")
        else:
            sections["NOT EXECUTED"].append("Python tests")

        if any(
            e.event_type == AuditEventType.TOOL_INVOKED
            and isinstance(e.payload, dict)
            and e.payload.get("tool") == "docker"
            for e in events
        ):
            sections["REAL PASS"].append("Docker build")
        else:
            sections["NOT EXECUTED"].append("Docker build")

        if AuditEventType.TERRAFORM_PLAN_COMPLETED in event_types:
            sections["REAL PASS"].append("Terraform validate")
        else:
            sections["NOT EXECUTED"].append("Terraform validate")

        if AuditEventType.SECURITY_SCAN_COMPLETED in event_types:
            sections["REAL PASS"].append("Trivy security scan")
        else:
            sections["NOT EXECUTED"].append("Trivy security scan")

        if AuditEventType.DEPLOYMENT_SUCCEEDED in event_types:
            sections["REAL PASS"].append("Azure deployment")
        elif AuditEventType.DEPLOYMENT_FAILED in event_types:
            sections["REAL FAIL"].append("Azure deployment")
        else:
            sections["NOT EXECUTED"].append("Azure deployment")

    if args.format == "json":
        data = {
            "project": session.project_root,
            "session_id": session.id,
            "started_at": str(session.started_at),
            "execution": sections,
            "learning_evidence": {
                k: [e.item for e in v] for k, v in experiences.items()
            },
        }
        out = json.dumps(data, indent=2)
    else:
        lines = [
            "DEVOPS LEARN // EVIDENCE REPORT",
            "",
            "PROJECT",
            session.project_root,
            "",
            "SESSION",
            str(session.started_at),
            "",
            "EXECUTION",
            "",
        ]

        for state in ["REAL PASS", "REAL FAIL", "SIMULATED", "NOT EXECUTED"]:
            for item in sections[state]:
                lines.extend([state, item, ""])

        lines.append("LEARNING EVIDENCE")
        if not experiences:
            lines.append("No evidence recorded in this session.")
        else:
            for concept, entries in experiences.items():
                for entry in entries:
                    lines.append(f"{concept:<19} {entry.state.value}")

        out = "\n".join(lines)

    if args.output:
        with open(args.output, "w") as f:
            f.write(out + "\n")
        print(f"Report written to {args.output}")
    else:
        print(out)
